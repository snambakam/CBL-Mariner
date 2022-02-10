Vendor:         Microsoft Corporation
Distribution:   Mariner
%undefine __cmake_in_source_build

%global version_major 1
%global version_minor 1
%global version_micro 0

Name:           sdbus-cpp
Version:        %{version_major}.%{version_minor}.%{version_micro}
Release:        2%{?dist}
Summary:        High-level C++ D-Bus library

License:        LGPLv2
URL:            https://github.com/Kistler-Group/sdbus-cpp
Source0:        %{url}/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildRequires:  cmake >= 3.12
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig(libsystemd) >= 236
BuildRequires:  doxygen

%description
High-level C++ D-Bus library for Linux designed to provide easy-to-use
yet powerful API in modern C++

%package devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Development files for %{name}.

%package tools
Summary:        Stub code generator for sdbus-c++
Requires:       %{name}%{?_isa} = %{version}-%{release}
BuildRequires:  pkgconfig(expat)
Obsoletes:      %{name}-xml2cpp < %{version}-%{release}

%description tools
The stub code generator for generating the adapter and proxy interfaces
out of the D-Bus IDL XML description.


%prep
%autosetup -p1


%build
cmake \
   -D CMAKE_INSTALL_PREFIX=%{_prefix} \
   -D BUILD_CODE_GEN=ON \
   -D CMAKE_BUILD_TYPE=Release \
   .
cmake --build .

%install
make install DESTDIR=%{buildroot}
rm -rf %{buildroot}%{_docdir}

%files
%{_lib64dir}/libsdbus-c++.so.%{version_major}
%{_lib64dir}/libsdbus-c++.so.%{version}
%dir %{_lib64dir}/cmake/sdbus-c++
%{_lib64dir}/cmake/sdbus-c++/*.cmake

%files devel
%{_lib64dir}/pkgconfig/sdbus-c++.pc
%{_lib64dir}/pkgconfig/sdbus-c++-tools.pc
%{_lib64dir}/libsdbus-c++.so
%{_includedir}/*

%files tools
%{_bindir}/sdbus-c++-xml2cpp
%dir %{_lib64dir}/cmake/sdbus-c++-tools
%{_lib64dir}/cmake/sdbus-c++-tools/*.cmake


%changelog
* Sat Jan 22 2022 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Tue Jan 04 2022 Marek Blaha <mblaha@redhat.com> - 1.1.0-1
- Update to release 1.1.0

* Tue Oct 26 2021 Marek Blaha <mblaha@redhat.com> - 1.0.0-1
- Update to release 1.0.0
- Change source tarball name to <name>-<version>.tar.gz

* Tue Oct 19 2021 Marek Blaha <mblaha@redhat.com> - 0.9.0-1
- Update to release 0.9.0

* Fri Jul 23 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.8.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Wed Jan 27 2021 Fedora Release Engineering <releng@fedoraproject.org> - 0.8.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Thu Dec 17 2020 Marek Blaha <mblaha@redhat.com> - 0.8.3-1
- Update to release 0.8.3

* Tue Oct 06 2020 Marek Blaha <mblaha@redhat.com> - 0.8.1-5
- Switch from make_build to cmake_build

* Tue Sep 22 2020 Jeff Law <law@redhat.com> - 0.8.1-4
- Use cmake_in_source_build to fix FTBFS due to recent cmake macro changes

* Sat Aug 01 2020 Fedora Release Engineering <releng@fedoraproject.org> - 0.8.1-3
- Second attempt - Rebuilt for
  https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Wed Jul 29 2020 Fedora Release Engineering <releng@fedoraproject.org> - 0.8.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Fri Feb 7 2020 Marek Blaha <mblaha@redhat.com> - 0.8.1-1
- Update to release 0.8.1

* Fri Jan 24 2020 Marek Blaha <mblaha@redhat.com> - 0.7.8-1
- Initial release 0.7.8
