%define debug_package %{nil}
Summary:        Microsoft .NET Core SDK
Name:           dotnet-sdk-3.1
Version:        3.1.105
Release:        1%{?dist}
Vendor:         Microsoft Corporation
Distribution:   Mariner
License:        MIT
Url:            https://github.com/dotnet/core
Group:          Development/Tools
Source0:        https://download.visualstudio.microsoft.com/download/pr/37268c18-226d-436b-b13c-4b77b7f42140/17e8a85360206006a557d634d16713cd/dotnet-sdk-3.1.105-linux-x64.tar.gz
ExclusiveArch:  x86_64

Requires:       dotnet-runtime-3.1
Requires:       icu

%description
.NET Core is a development platform that you can use to build command-line
applications, microservices and modern websites.

%prep
%setup -qc dotnet-sdk-%{version}

%build

%install
mkdir -p %{buildroot}%{_libdir}/dotnet/sdk
mkdir -p %{buildroot}%{_docdir}/dotnet-sdk-%{version}
cp -r sdk/%{version} %{buildroot}%{_libdir}/dotnet/sdk
cp LICENSE.txt ThirdPartyNotices.txt %{buildroot}%{_docdir}/dotnet-sdk-%{version}

%files
%license LICENSE.txt
    %defattr(-,root,root,0755)
    %{_libdir}/*
    %{_docdir}/*

%changelog
*   Fri Jun 19 2020 Andrew Phelps <anphel@microsoft.com> 3.1.105-1
-   Update version to 3.1.105
*   Sat May 09 2020 Nick Samson <nisamson@microsoft.com> 3.1.102-5
-   Added %%license line automatically
*   Tue May 05 2020 Emre Girgin <mrgirgin@microsoft.com> 3.1.102-4
-   Renaming dotnet-runtime to dotnet-runtime-3.1
*   Mon May 04 2020 Emre Girgin <mrgirgin@microsoft.com> 3.1.102-3
-   Renaming dotnet-sdk to dotnet-sdk-3.1
*   Mon May 04 2020 Emre Girgin <mrgirgin@microsoft.com> 3.1.102-2
-   Replace BuildArch with ExclusiveArch
*   Mon Mar 30 2020 Andrew Phelps <anphel@microsoft.com> 3.1.102-1
-   Update to dotnet 3.1.102. License verified.
*   Tue Sep 03 2019 Mateusz Malisz <mamalisz@microsoft.com> 2.1.403-2
-   Initial CBL-Mariner import from Photon (license: Apache2).
*   Wed Dec 05 2018 Ajay Kaher <akaher@vmware.com> 2.1.403-1
-   upgraded to version 2.1.403
*   Wed Jan 31 2018 Priyesh Padmavilasom <ppadmavilasom@vmware.com> 2.1.4-1
-   Initial build for photon
