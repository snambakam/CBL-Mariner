// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

package rpmrepocloner

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"microsoft.com/pkggen/internal/buildpipeline"
	"microsoft.com/pkggen/internal/logger"
	"microsoft.com/pkggen/internal/packagerepo/repocloner"
	"microsoft.com/pkggen/internal/packagerepo/repomanager/rpmrepomanager"
	"microsoft.com/pkggen/internal/pkgjson"
	"microsoft.com/pkggen/internal/safechroot"
	"microsoft.com/pkggen/internal/shell"
)

const (
	squashChrootRunErrors  = false
	chrootDownloadDir      = "/outputrpms"
	leaveChrootFilesOnDisk = false
	updateRepoIDPrefix     = "mariner-official-update*"
)

var (
	// Every valid line will be of the form: <package>-<version>.<arch> : <Description>
	packageLookupNameMatchRegex = regexp.MustCompile(`^\s*([^:]+(x86_64|aarch64|noarch))\s*:`)

	// Every valid line will be of the form: <package_name>.<architecture> <version>.<dist>  fetcher-cloned-repo
	listedPackageRegex = regexp.MustCompile(`^\s*(?P<Name>[a-zA-Z0-9_+-]+)\.(?P<Arch>[a-zA-Z0-9_+-]+)\s*(?P<Version>[a-zA-Z0-9._+-]+)\.(?P<Dist>[a-zA-Z0-9_+-]+)\s*fetcher-cloned-repo`)
)

const (
	listMatchSubString = iota
	listPackageName    = iota
	listPackageArch    = iota
	listPackageVersion = iota
	listPackageDist    = iota
	listMaxMatchLen    = iota
)

// RpmRepoCloner represents an RPM repository cloner.
type RpmRepoCloner struct {
	chroot        *safechroot.Chroot
	useUpdateRepo bool
	cloneDir      string
}

// New creates a new RpmRepoCloner
func New() *RpmRepoCloner {
	return &RpmRepoCloner{}
}

// Initialize initializes rpmrepocloner, enabling Clone() to be called.
//  - destinationDir is the directory to save RPMs
//  - tmpDir is the directory to create a chroot
//  - workerTar is the path to the worker tar used to seed the chroot
//  - existingRpmsDir is the directory with prebuilt RPMs
//  - useUpdateRepo if set, the upstream update repository will be used.
//  - repoDefinitions is a list of repo files to use when cloning RPMs
func (r *RpmRepoCloner) Initialize(destinationDir, tmpDir, workerTar, existingRpmsDir string, useUpdateRepo bool, repoDefinitions []string) (err error) {
	const (
		isExistingDir = false

		bindFsType = ""
		bindData   = ""

		chrootLocalRpmsDir = "/localrpms"

		overlayWorkDirectory  = "/overlaywork/workdir"
		overlayUpperDirectory = "/overlaywork/upper"
		overlaySource         = "overlay"
	)

	r.useUpdateRepo = useUpdateRepo
	if !useUpdateRepo {
		logger.Log.Warnf("Disabling update repo")
	}

	// Ensure that if initialization fails, the chroot is closed
	defer func() {
		if err != nil {
			logger.Log.Warnf("Failed to initialize cloner. Error: %s", err)
			if r.chroot != nil {
				closeErr := r.chroot.Close(leaveChrootFilesOnDisk)
				if closeErr != nil {
					logger.Log.Panicf("Unable to close chroot on failed initialization. Error: %s", closeErr)
				}
			}
		}
	}()

	// Create the directory to download into
	err = os.MkdirAll(destinationDir, os.ModePerm)
	if err != nil {
		logger.Log.Warnf("Could not create download directory (%s)", destinationDir)
		return
	}

	// Setup the chroot
	logger.Log.Infof("Creating cloning environment to populate (%s)", destinationDir)
	r.chroot = safechroot.NewChroot(tmpDir, isExistingDir)

	r.cloneDir = destinationDir

	// Setup mount points for the chroot.
	//
	// 1) Mount the provided directory of existings RPMs into the chroot as an overlay,
	// ensuring the chroot can read the files, but not alter the actual directory outside
	// the chroot.
	//
	// 2) Mount the directory to download RPMs into as a bind, allowing the chroot to write
	// files into it.
	overlayMount, overlayExtraDirs := safechroot.NewOverlayMountPoint(r.chroot.RootDir(), overlaySource, chrootLocalRpmsDir, existingRpmsDir, overlayUpperDirectory, overlayWorkDirectory)
	extraMountPoints := []*safechroot.MountPoint{
		overlayMount,
		safechroot.NewMountPoint(destinationDir, chrootDownloadDir, bindFsType, safechroot.BindMountPointFlags, bindData),
	}

	// Also request that /overlaywork is created before any chroot mounts happen so the overlay can
	// be created succesfully
	err = r.chroot.Initialize(workerTar, overlayExtraDirs, extraMountPoints)
	if err != nil {
		r.chroot = nil
		return
	}

	logger.Log.Info("Initializing local RPM repository")
	err = r.initializeMountedChrootRepo(chrootLocalRpmsDir)
	if err != nil {
		return
	}

	logger.Log.Info("Initializing repository configurations")
	err = r.initializeRepoDefinitions(repoDefinitions)
	if err != nil {
		return
	}

	return
}

// AddNetworkFiles adds files needed for networking capabilities into the cloner.
func (r *RpmRepoCloner) AddNetworkFiles(tlsClientCert, tlsClientKey string) (err error) {
	if tlsClientCert == "" || tlsClientKey == "" {
		err = fmt.Errorf("one of tlsClientCert(%s) or tlsClientKey(%s) is not set", tlsClientCert, tlsClientKey)
		return
	}
	files := []safechroot.FileToCopy{
		{Src: "/etc/resolv.conf", Dest: "/etc/resolv.conf"},
		{Src: tlsClientCert, Dest: "/etc/tdnf/mariner_user.crt"},
		{Src: tlsClientKey, Dest: "/etc/tdnf/mariner_user.key"},
	}
	err = r.chroot.AddFiles(files...)
	return
}

// initializeRepoDefinitions will configure the chroot's repo files to match those
// provided by the caller.
func (r *RpmRepoCloner) initializeRepoDefinitions(repoDefinitions []string) (err error) {
	// ============== TDNF SPECIFIC IMPLEMENTATION ==============
	// Unlike some other package managers, TDNF has no notion of repository priority.
	// It reads the repo files using `readdir`, which should be assumed to be random ordering.
	//
	// In order to simulate repository priority, concatenate all requested repofiles into a single file.
	// TDNF will read the file top-down. It will then parse the results into a linked list, meaning
	// the first repo entry in the file is the first to be checked.
	const chrootRepoFile = "/etc/yum.repos.d/allrepos.repo"

	fullRepoFilePath := filepath.Join(r.chroot.RootDir(), chrootRepoFile)

	// Create the directory for the repo file
	err = os.MkdirAll(filepath.Dir(fullRepoFilePath), os.ModePerm)
	if err != nil {
		logger.Log.Warnf("Could not create directory for chroot repo file (%s)", fullRepoFilePath)
		return
	}

	dstFile, err := os.OpenFile(fullRepoFilePath, os.O_RDWR|os.O_CREATE, os.ModePerm)
	if err != nil {
		return
	}
	defer dstFile.Close()

	// Append all repo files together into a single repo file.
	// Assume the order of repoDefinitions indicates their relative priority.
	for _, repoFilePath := range repoDefinitions {
		err = appendRepoFile(repoFilePath, dstFile)
		if err != nil {
			return
		}
	}

	return
}

func appendRepoFile(repoFilePath string, dstFile *os.File) (err error) {
	repoFile, err := os.Open(repoFilePath)
	if err != nil {
		return
	}
	defer repoFile.Close()

	_, err = io.Copy(dstFile, repoFile)
	if err != nil {
		return
	}

	// Append a new line
	_, err = dstFile.WriteString("\n")
	return
}

// initializeMountedChrootRepo will initialize a local RPM repository inside the chroot.
func (r *RpmRepoCloner) initializeMountedChrootRepo(repoDir string) (err error) {
	return r.chroot.Run(func() (err error) {
		return rpmrepomanager.CreateRepo(repoDir)
	})
}

// SearchAndClone attempts to find a package which supplies the requested file or package. It
// wraps Clone() to acquire the requested package once found.
func (r *RpmRepoCloner) SearchAndClone(cloneDeps bool, singlePackageToClone *pkgjson.PackageVer) (err error) {
	var (
		pkgName string
		stderr  string
	)

	err = r.chroot.Run(func() (err error) {
		args := []string{
			"provides",
			singlePackageToClone.Name,
		}

		if !r.useUpdateRepo {
			args = append(args, fmt.Sprintf("--disablerepo=%s", updateRepoIDPrefix))
		}

		stdout, stderr, err := shell.Execute("tdnf", args...)
		logger.Log.Debugf("tdnf search for dependency '%s':\n%s", singlePackageToClone.Name, stdout)

		if err != nil {
			logger.Log.Errorf("Failed to lookup dependency '%s', tdnf error: '%s'", singlePackageToClone.Name, stderr)
			return
		}

		splitStdout := strings.Split(stdout, "\n")
		for _, line := range splitStdout {
			matches := packageLookupNameMatchRegex.FindStringSubmatch(line)
			if len(matches) == 0 {
				continue
			}
			// Local sources are listed last, keep searching for the last possible match
			pkgName = matches[1]
			logger.Log.Debugf("'%s' is available from package '%s'", singlePackageToClone.Name, pkgName)
		}
		return
	})

	if err != nil {
		logger.Log.Error(stderr)
		return
	}

	logger.Log.Warnf("Translated '%s' to package '%s'", singlePackageToClone.Name, pkgName)

	err = r.Clone(cloneDeps, &pkgjson.PackageVer{Name: pkgName})
	return
}

// Clone clones the provided list of packages.
// If cloneDeps is set, package dependencies will also be cloned.
func (r *RpmRepoCloner) Clone(cloneDeps bool, packagesToClone ...*pkgjson.PackageVer) (err error) {
	const (
		unresolvedOutputPrefix  = "No package"
		toyboxConflictsPrefix   = "toybox conflicts"
		unresolvedOutputPostfix = "available"

		strictComparisonOperator          = "="
		lessThanOrEqualComparisonOperator = "<="
		versionSuffixFormat               = "-%s"
	)

	for _, pkg := range packagesToClone {
		builder := strings.Builder{}
		builder.WriteString(pkg.Name)

		// Treat <= as =
		// Treat > and >= as "latest"
		if pkg.Condition == strictComparisonOperator || pkg.Condition == lessThanOrEqualComparisonOperator {
			builder.WriteString(fmt.Sprintf(versionSuffixFormat, pkg.Version))
		}

		err = r.chroot.Run(func() (err error) {
			args := []string{
				"--destdir",
				chrootDownloadDir,
				builder.String(),
			}

			if !r.useUpdateRepo {
				args = append(args, fmt.Sprintf("--disablerepo=%s", updateRepoIDPrefix))
			}

			if cloneDeps {
				args = append([]string{"download", "--alldeps"}, args...)
			} else {
				args = append([]string{"download-nodeps"}, args...)
			}

			stdout, stderr, err := shell.Execute("tdnf", args...)

			logger.Log.Debugf("stdout: %s", stdout)
			logger.Log.Debugf("stderr: %s", stderr)

			if err != nil {
				logger.Log.Errorf("tdnf error (will continue if the only errors are toybox conflicts):\n '%s'", stderr)
			}

			// ============== TDNF SPECIFIC IMPLEMENTATION ==============
			// Check if TDNF could not resolve a given package. If TDNF does not find a requested package,
			// it will not error. Instead it will print a message to stdout. Check for this message.
			//
			// *NOTE*: TDNF will attempt best effort. If N packages are requested, and 1 cannot be found,
			// it will still download N-1 packages while also printing the message.
			splitStdout := strings.Split(stdout, "\n")
			for _, line := range splitStdout {
				trimmedLine := strings.TrimSpace(line)
				// Toybox conflicts are a known issue, reset the err value if encountered
				if strings.HasPrefix(trimmedLine, toyboxConflictsPrefix) {
					logger.Log.Warn("Ignoring known toybox conflict")
					err = nil
					continue
				}
				// If a package was not available, update err
				if strings.HasPrefix(trimmedLine, unresolvedOutputPrefix) && strings.HasSuffix(trimmedLine, unresolvedOutputPostfix) {
					err = fmt.Errorf(trimmedLine)
					break
				}
			}

			return
		})

		if err != nil {
			return
		}
	}

	return
}

// ConvertDownloadedPackagesIntoRepo initializes the downloaded RPMs into an RPM repository.
func (r *RpmRepoCloner) ConvertDownloadedPackagesIntoRepo() (err error) {
	fullRpmDownloadDir := buildpipeline.GetRpmsDir(r.chroot.RootDir(), chrootDownloadDir)

	err = rpmrepomanager.OrganizePackagesByArch(fullRpmDownloadDir, fullRpmDownloadDir)
	if err != nil {
		return
	}

	err = r.initializeMountedChrootRepo(chrootDownloadDir)
	return
}

// ClonedRepoContents returns the packages contained in the cloned repository.
func (r *RpmRepoCloner) ClonedRepoContents() (repoContents *repocloner.RepoContents, err error) {
	const fetcherRepoID = "fetcher-cloned-repo"

	repoContents = &repocloner.RepoContents{}
	onStdout := func(args ...interface{}) {
		if len(args) == 0 {
			return
		}

		line := args[0].(string)
		matches := listedPackageRegex.FindStringSubmatch(line)
		if len(matches) != listMaxMatchLen {
			return
		}

		pkg := &repocloner.RepoPackage{
			Name:         matches[listPackageName],
			Version:      matches[listPackageVersion],
			Architecture: matches[listPackageArch],
			Distribution: matches[listPackageDist],
		}

		repoContents.Repo = append(repoContents.Repo, pkg)
	}

	err = r.chroot.Run(func() (err error) {
		// Disable all repositories except the fetcher repository (the repository with the cloned packages)
		tdnfArgs := []string{
			"list",
			"ALL",
			"--disablerepo=*",
			fmt.Sprintf("--enablerepo=%s", fetcherRepoID),
		}
		return shell.ExecuteLiveWithCallback(onStdout, logger.Log.Warn, "tdnf", tdnfArgs...)
	})

	return
}

// CloneDirectory returns the directory where cloned packages are saved.
func (r *RpmRepoCloner) CloneDirectory() string {
	return r.cloneDir
}

// Close closes the given RpmRepoCloner.
func (r *RpmRepoCloner) Close() error {
	return r.chroot.Close(leaveChrootFilesOnDisk)
}
