Summary:        DNS proxy with integrated DHCP server
Name:           dnsmasq
Version:        2.79
Release:        11%{?dist}
License:        GPLv2 or GPLv3
Group:          System Environment/Daemons
URL:            http://www.thekelleys.org.uk/dnsmasq/
Source0:        http://www.thekelleys.org.uk/%{name}/%{name}-%{version}.tar.xz
Vendor:         Microsoft Corporation
Distribution:   Mariner
Patch0:         fix-missing-ioctl-SIOCGSTAMP-add-sockios-header-linux-5.2.patch
Patch1:         CVE-2019-14834.patch

BuildRequires:  kernel-headers

%description
Dnsmasq a lightweight, caching DNS proxy with integrated DHCP server.

%prep
%setup -q
%patch0 -p1
%patch1 -p1

%build
make %{?_smp_mflags}

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}%{_mandir}/man8
mkdir -p %{buildroot}%{_mandir}/man1
mkdir -p %{buildroot}%{_sharedstatedir}/dnsmasq
mkdir -p %{buildroot}%{_sysconfdir}/dnsmasq.d
mkdir -p %{buildroot}%{_sysconfdir}/dbus-1/system.d
mkdir -p %{buildroot}%{_bindir}
install src/dnsmasq %{buildroot}%{_sbindir}/dnsmasq
install dnsmasq.conf.example %{buildroot}%{_sysconfdir}/dnsmasq.conf
install dbus/dnsmasq.conf %{buildroot}%{_sysconfdir}/dbus-1/system.d/
install -m 644 man/dnsmasq.8 %{buildroot}%{_mandir}/man8/
install -D trust-anchors.conf %{buildroot}%{_datadir}/%{name}/trust-anchors.conf

install -m 755 contrib/wrt/lease_update.sh %{buildroot}%{_sbindir}/lease_update.sh

mkdir -p %{buildroot}/usr/lib/systemd/system
cat << EOF >> %{buildroot}/usr/lib/systemd/system/dnsmasq.service
[Unit]
Description=A lightweight, caching DNS proxy
After=network.target

[Service]
ExecStart=/usr/sbin/dnsmasq -k
Restart=always

[Install]
WantedBy=multi-user.target
EOF

%post

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%license COPYING
%{_libdir}/systemd/*
%exclude %{_libdir}/debug
%{_sbindir}/*
%{_mandir}/*
%{_sysconfdir}/*
%dir %{_sharedstatedir}
%config  /usr/share/dnsmasq/trust-anchors.conf

%changelog
*   Thu Jun 18 2020 Pawel Winogrodzki <pawelwi@microsoft.com> 2.79-11
-   Removing runtime dependency on a specific kernel package.
*   Thu Jun 11 2020 Christopher Co <chrco@microsoft.com> - 2.79-10
-   Remove KERNEL_VERSION macro from BuildRequires
*   Thu May 21 2020 Ruying Chen <v-ruyche@microsoft.com> - 2.79-9
-   Fix CVE-2019-14834
*   Sat May 09 00:21:16 PST 2020 Nick Samson <nisamson@microsoft.com> - 2.79-8
-   Added %%license line automatically
*   Thu Apr 30 2020 Emre Girgin <mrgirgin@microsoft.com> 2.79-7
-   Renaming linux-api-headers to kernel-headers
*   Tue Apr 28 2020 Emre Girgin <mrgirgin@microsoft.com> 2.79-6
-   Renaming linux to kernel
*   Thu Apr 09 2020 Pawel Winogrodzki <pawelwi@microsoft.com> 2.79-5
-   Fixed "Source0" tag.
-   Removed "%%define sha1".
*   Mon Mar 23 2020 Christopher Co <chrco@microsoft.com> 2.79-4
-   Remove KERNEL_RELEASE macro from required packages
*   Wed Jan 08 2020 Christopher Co <chrco@microsoft.com> 2.79-3
-   Fix missing SIOCGSTAMP ioctl definition due to linux 5.2 header refactor
-   Verified License
*   Tue Sep 03 2019 Mateusz Malisz <mamalisz@microsoft.com> 2.79-2
-   Initial CBL-Mariner import from Photon (license: Apache2).
*   Mon Sep 10 2018 Ajay Kaher <akaher@vmware.com> 2.79-1
-   Upgrading to version 2.79
*   Tue Feb 13 2018 Xiaolin Li <xiaolinl@vmware.com> 2.76-5
-   Fix CVE-2017-15107
*   Mon Nov 13 2017 Vinay Kulkarni <kulkarniv@vmware.com> 2.76-4
-   Always restart dnsmasq service on exit
*   Wed Oct 11 2017 Alexey Makhalov <amakhalov@vmware.com> 2.76-3
-   Fix CVE-2017-13704
*   Wed Sep 27 2017 Alexey Makhalov <amakhalov@vmware.com> 2.76-2
-   Fix CVE-2017-14491..CVE-2017-14496
*   Sun Nov 27 2016 Vinay Kulkarni <kulkarniv@vmware.com> 2.76-1
-   Upgrade to 2.76 to address CVE-2015-8899
*   Tue May 24 2016 Priyesh Padmavilasom <ppadmavilasom@vmware.com> 2.75-2
-   GA - Bump release of all rpms
*   Mon Apr 18 2016 Xiaolin Li <xiaolinl@vmware.com> 2.75-1
-   Initial version
