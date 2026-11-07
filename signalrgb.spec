# Unofficial Fedora packaging of SignalRGB (https://signalrgb.com).
#
# SignalRGB does not ship a native RPM (their install.sh only supports Arch and
# Debian/Ubuntu apt). This spec pulls the vendor's Ubuntu .deb directly from
# their package server at build time, unwraps it, and republishes the payload
# under the same paths the upstream packages use:
#
#   /opt/signalrgb/<app artillery>     app + bundled Qt6/ffmpeg/ICU (private, LD_LIBRARY_PATH)
#   /usr/bin/signalrgb                 launcher shell shim
#   /etc/udev/rules.d/72-signalrgb.rules
#   /usr/share/applications/signalrgb.desktop
#   /usr/share/icons/hicolor/, /usr/share/pixmaps/
#
# Bundled libraries are private (loaded via LD_LIBRARY_PATH from /opt/signalrgb/lib),
# so we filter them out of both auto-Provides and auto-Requires and let rpm's
# ELF dep generator pin real system sonames instead. This is deliberately NOT
# Alien-style ldconfig repackaging.
#
# Distribution of the binary payload is governed by the SignalRGB end user
# license agreement (https://signalrgb.com/eula). This package ships it
# unmodified.

%global buildrev 7617
# Body of the __requires_exclude alternation: bundled sonames (in
# /opt/signalrgb/lib) plus Debian-only sonames/symbols Fedora ships
# differently. Keep in sync with the Requires list below.
#  Bundled (private Qt6/ffmpeg/ICU/etc):
%global bundled_body lib(AppCore|Qt6.*|avcodec|avformat|avutil|datachannel|git2|icudata|icui18n|icuuc|swresample|swscale|Ultralight|UltralightCore|WebCore)\.so.*
#  Debian-vs-Fedora divergences (see compat symlinks in %install for
#  libbz2/libtesseract; Fedora's libcurl simply exports no symbol node):
#   - libbz2.so.1.0 (Fedora 45 rebuilds with soname libbz2.so.1)
#   - libcurl.so.4(CURL_OPENSSL_4)
#   - libtesseract.so.5 (Fedora 45 ships libtesseract.so.5.5)
# NOTE: rpm matches __requires_exclude against the dependency name WITHOUT the
# trailing "()(64bit)" architectural adornment, so these must be prefix-based
# (verified experimentally; suffix-exact patterns never match).
%global excluded_body lib(bz2\.so\.1\.0|tesseract\.so\.5|curl\.so\.4\(CURL_OPENSSL_4\)).*

%global upstream_deb signalrgb_%{version}-%{buildrev}_amd64.deb
%global upstream_url https://pkgs.signalrgb.com/apt/pool/stable/main/s/signalrgb/%{upstream_deb}

# sha256 of the pinned upstream .deb (from their apt repo Packages index)
%global deb_sha256 5c8c29d193f75ff1d02874bbd32ca2b130b75a0312bb9d6fafea156b3da2599c

# Vendor spends their own cryptographic bytes elsewhere; here we rely on:
#  - pinned SHA256 of the source .deb above
#  - no bundled-library Provides
#  - exact soname Requires generated from the shipped ELF files
%global debug_package %{nil}
%global __brp_check_rpaths %{nil}
%global __provides_exclude_from ^/opt/signalrgb/
%global __requires_exclude ^(%{bundled_body}|%{excluded_body})$

Name:           signalrgb
Version:        2.5.86
Release:        %{buildrev}%{?dist}
Summary:        Control and sync your RGB with one app
License:        SignalRGB EULA
URL:            https://signalrgb.com
Source0:        %{upstream_url}
ExclusiveArch:  x86_64

Requires:       shadow-utils
Requires:       systemd
Requires:       systemd-udev
# Package-level deps replacing the vendors' Debian soname Requires that
# Fedora satisfies differently (see excluded_sonames above)
Requires:       bzip2-libs
Requires:       libcurl
Requires:       tesseract-libs
# OCR text data for the tesseract dependency (upstream: tesseract-ocr-eng)
Requires:       tesseract-langpack-eng

Conflicts:      signalrgb <= 0

%description
SignalRGB (https://signalrgb.com) lets you control and sync your RGB devices
from one application with game integrations and community effects.

This is an UNOFFICIAL repackaging for Fedora/RHEL-family systems, built from
the vendor's Ubuntu .deb. The application payload and bundled libraries are
shipped unmodified under /opt/signalrgb. Use of the software remains subject
to the SignalRGB EULA. Not affiliated with or endorsed by SignalRGB.

%prep
echo '%{deb_sha256}  %{_sourcedir}/%{upstream_deb}' | sha256sum -c -
rm -rf data && mkdir data
# Unwrap the .deb (ar) then unwrap the data payload (tar handles zstd/xz/gz
# transparently, so the payload format may change across upstream versions).
databall="$(ar t %{SOURCE0} | grep -E '^data\.tar\.' | head -n1)"
ar p %{SOURCE0} "$databall" > data/tmp.tar
tar -xf data/tmp.tar -C data
rm -f data/tmp.tar

%install
mkdir -p %{buildroot}
cp -a data/. %{buildroot}/

# Compat with Fedora soname differences (private to the app: /opt/signalrgb/lib
# is already first on the shim's LD_LIBRARY_PATH, so these shadow-less files
# never leak into the system linker namespace).
#   libbz2.so.1.0 -> libbz2.so.1     (Debian vs Fedora=45 rebuild soname)
#   libtesseract.so.5 -> .so.5.5     (same)
ln -s ../../../usr/lib64/libbz2.so.1 %{buildroot}/opt/signalrgb/lib/libbz2.so.1.0
ln -s ../../../usr/lib64/libtesseract.so.5.5 %{buildroot}/opt/signalrgb/lib/libtesseract.so.5

%files
/opt/signalrgb
/usr/bin/signalrgb
/usr/share/applications/signalrgb.desktop
/usr/share/icons/hicolor
/usr/share/pixmaps/signalrgb.png
/etc/udev/rules.d/72-signalrgb.rules

%post
# The vendored udev rules reference Debian group names (plugdev, i2c). Fedora
# does not ship these groups; create them if missing so GROUP= assignments do
# not error out. Device access for the common cases comes from the uaccess tag
# regardless (systemd-logind ACLs).
getent group plugdev >/dev/null 2>&1 || groupadd -f -r plugdev || :
getent group i2c >/dev/null 2>&1 || groupadd -f -r i2c || :

if [ -x /usr/bin/udevadm ]; then
  /usr/bin/udevadm control --reload-rules >/dev/null 2>&1 || :
  /usr/bin/udevadm trigger >/dev/null 2>&1 || :
fi

if [ -x /usr/bin/gtk-update-icon-cache ]; then
  /usr/bin/gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || :
fi
if [ -x /usr/bin/update-desktop-database ]; then
  /usr/bin/update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%postun
if [ -x /usr/bin/update-desktop-database ]; then
  /usr/bin/update-desktop-database /usr/share/applications >/dev/null 2>&1 || :
fi

%changelog
* Sat Nov 07 2026 Fiction Maintainer <auto@signalrgb-repack.local> - 2.5.86-7617
- Drop soname requires for libbz2.so.1.0 / libcurl.so.4(CURL_OPENSSL_4) /
  libtesseract.so.5 (Debian-only naming or symbol versions); replace with
  package-level requires (bzip2-libs, libcurl, tesseract-libs).
- Add private /opt/signalrgb/lib compat symlinks (libbz2, libtesseract).
* Fri Nov 06 2026 Fiction Maintainer <auto@signalrgb-repack.local> - 2.5.86-7617
- Initial RPM repackage from upstream Ubuntu .deb (2.5.86-7617).
- /opt/signalrgb payload from vendor data.tar, unmodified.
- Bundled Qt6/ffmpeg/ICU kept private via /opt/signalrgb; system soname deps
  generated by rpmbuild.
- udev rules installed to /etc/udev/rules.d/72-signalrgb.rules with rule
  reload/trigger in %post.
