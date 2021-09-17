%global debug_package %{nil}
Summary:        The Kubernetes Package Manager
Name:           helm
Version:        3.4.1
Release:        2%{?dist}
License:        Apache 2.0
Vendor:         Microsoft Corporation
Distribution:   Mariner
Group:          Applications/Networking
URL:            https://github.com/helm/helm
#Source0:      https://github.com/%{name}/%{name}/archive/v%{version}.tar.gz
Source0:        %{name}-%{version}.tar.gz
# Below is a manually created tarball, no download link.
# We're using pre-populated Go modules from this tarball, since network is disabled during build time.
# How to re-build this file:
#   1. wget https://github.com/helm/helm/archive/v3.4.1.tar.gz -O %%{name}-%%{version}.tar.gz
#   2. tar -xf %%{name}-%%{version}.tar.gz
#   3. cd %%{name}-%%{version}
#   4. go mod vendor
#   5. tar  --sort=name \
#           --mtime="2021-04-26 00:00Z" \
#           --owner=0 --group=0 --numeric-owner \
#           --pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime \
#           -cf %%{name}-%%{version}-vendor.tar.gz vendor
#
Source1:        %{name}-%{version}-vendor.tar.gz
BuildRequires:  golang >= 1.15.5

%description
Helm is a tool that streamlines installing and managing Kubernetes applications. Think of it like apt/yum/homebrew for Kubernetes.

%prep
%setup -q

%build
tar -xf %{SOURCE1} --no-same-owner
export VERSION=%{version}
for cmd in cmd/* ; do
    go build -tags '' -ldflags '-w -s -X helm.sh/helm/v3/internal/version.version=v$VERSION -X helm.sh/helm/v3/internal/version.metadata= -X helm.sh/helm/v3/internal/version.gitCommit= -X helm.sh/helm/v3/internal/version.gitTreeState=clean ' \
    -mod=vendor -v -o $(basename $cmd) ./$cmd
done

%install
install -d -m 755 %{buildroot}%{_bindir}
install -m 755 ./helm %{buildroot}%{_bindir}

%files
%license LICENSE
%doc ADOPTERS.md SECURITY.md code-of-conduct.md CONTRIBUTING.md README.md
%{_bindir}/helm

%changelog
* Tue Aug 17 2021 Henry Li <lihl@microsoft.com> - 3.4.1-2
- Update and rename vendor source tarball
- Use go to build the project from vendor source
- Remove glide and ca-certificates from BR
- Modify file section to add license and document files

* Wed Nov 25 2020 Suresh Babu Chalamalasetty <schalam@microsoft.com> 3.4.1-1
- Update helm version 3

* Tue Jun 02 2020 Paul Monson <paulmon@microsoft.com> 2.14.3-2
- Rename go to golang
- Add ca-certificates temporarily

* Thu Oct 17 2019 Andrew Phelps <anphel@microsoft.com> 2.14.3-1
- Original version for CBL-Mariner