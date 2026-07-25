#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
Scaffold a modern SwiftUI macOS app project with linting, formatting,
and testing wired up from the start.

Generates:
  - SwiftUI app target (feature-based folder layout)
  - Unit test target (Swift Testing) + UI test target (XCTest)
  - project.yml for XcodeGen (so `xcodegen generate` produces the .xcodeproj —
    scripting a real .pbxproj by hand is not practical, XcodeGen is the
    standard workaround)
  - .swiftlint.yml + regular and analyzer-rule SwiftLint checks
  - .periphery.yml + Periphery dead-code analysis across all SwiftPM targets
  - .swift-format config
  - .pre-commit-config.yaml (auto-formats on commit)
  - GitHub Actions CI workflow (lint + analyzer + dead-code + format-check + test)
  - Makefile for local one-liners
  - LICENSE (MIT)

Usage:
  ./setup_macos_project.py -h
  ./setup_macos_project.py MyApp
  ./setup_macos_project.py MyApp --bundle-id com.example.myapp -o ~/dev -v
  ./setup_macos_project.py MyApp --overwrite -vv

Requires (not installed by this script, just needed afterwards):
  - Xcode (with command line tools)
  - xcodegen        brew install xcodegen
  - swiftlint       brew install swiftlint   (or via project.yml plugin)
  - periphery       brew install periphery
  - swift format     provided by the Swift toolchain (run as `swift format`)
  - pre-commit      brew install pre-commit  (optional)
"""

import datetime
import logging
import shutil
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

# --------------------------------------------------------------------------
# Logging / CLI (boilerplate)
# --------------------------------------------------------------------------


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument("app_name", help="App / project name, e.g. MyApp")
    parser.add_argument(
        "--bundle-id",
        dest="bundle_id",
        default=None,
        help="Bundle identifier, e.g. com.example.myapp (default: com.example.<lowercased-app-name>)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default=".",
        help="Directory to create the project folder in (default: current directory)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the destination folder if it already exists",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


# --------------------------------------------------------------------------
# File writing helper
# --------------------------------------------------------------------------


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip("\n"), encoding="utf-8")
    logging.info(f"wrote {path}")


def touch_gitkeep(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    (path / ".gitkeep").write_text("", encoding="utf-8")
    logging.debug(f"created dir {path}")


# --------------------------------------------------------------------------
# Swift file templates
# --------------------------------------------------------------------------


def app_entry_swift(app_name: str) -> str:
    return f"""
import SwiftData
import SwiftUI

@main
struct {app_name}App: App {{
    @State private var appState = AppState()

    var body: some Scene {{
        WindowGroup {{
            ContentView()
                .environment(appState)
        }}
        .modelContainer(PersistenceController.container)
        .commands {{
            SidebarCommands()
        }}

        Settings {{
            SettingsView()
                .environment(appState)
        }}
    }}
}}
"""


def app_state_swift() -> str:
    return """
import Observation

@Observable
final class AppState {
    var isLoading: Bool = false
    var selectedItemID: Item.ID?
}
"""


def content_view_swift() -> str:
    return """
import SwiftUI

struct ContentView: View {
    @Environment(AppState.self) private var appState
    @State private var items: [Item] = []

    var body: some View {
        NavigationSplitView {
            List(items, selection: Bindable(appState).selectedItemID) { item in
                Text(item.name)
                    .tag(item.id)
            }
            .navigationTitle("Items")
        } detail: {
            if let selected = items.first(where: { $0.id == appState.selectedItemID }) {
                Text(selected.name)
                    .font(.title)
                    .padding()
            } else {
                ContentUnavailableView("Select an item", systemImage: "sidebar.left")
            }
        }
        .tint(AppColor.accent)
        .background(AppColor.background)
        .overlay {
            if appState.isLoading {
                ProgressView()
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(AppState())
}
"""


def item_model_swift() -> str:
    return """
import Foundation

struct Item: Identifiable, Hashable, Codable {
    let id: UUID
    var name: String
    var isComplete: Bool

    init(id: UUID = UUID(), name: String, isComplete: Bool = false) {
        self.id = id
        self.name = name
        self.isComplete = isComplete
    }

    enum ValidationError: Error {
        case emptyName
    }

    static func validate(name: String) throws {
        if name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            throw ValidationError.emptyName
        }
    }
}
"""


def persistence_controller_swift(app_name: str) -> str:
    return f"""
import SwiftData

@MainActor
enum PersistenceController {{
    static let container: ModelContainer = {{
        let schema = Schema([])
        let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
        do {{
            return try ModelContainer(for: schema, configurations: [configuration])
        }} catch {{
            fatalError("Failed to create ModelContainer for {app_name}: \\(error)")
        }}
    }}()
}}
"""


def settings_view_swift() -> str:
    return """
import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        TabView {
            GeneralSettingsTab(appState: appState)
                .tabItem { Label("General", systemImage: "gearshape") }
        }
        .frame(width: 420, height: 240)
    }
}

private struct GeneralSettingsTab: View {
    @Bindable var appState: AppState
    @State private var viewModel = SettingsViewModel()

    var body: some View {
        Form {
            Text("General settings go here.")
            Toggle("Launch at login", isOn: $viewModel.launchAtLogin)
            Toggle("Show loading state", isOn: $appState.isLoading)
        }
        .padding()
    }
}

#Preview {
    SettingsView()
        .environment(AppState())
}
"""


def settings_view_model_swift() -> str:
    return """
import Observation

@Observable
final class SettingsViewModel {
    var launchAtLogin: Bool = false
}
"""


def colors_swift() -> str:
    return """
import SwiftUI

enum AppColor {
    static let accent = Color.accentColor
    static let background = Color(nsColor: .windowBackgroundColor)
}
"""


def item_tests_swift(app_name: str) -> str:
    return f"""
import Testing
@testable import {app_name}

@Suite("Item Model Tests")
struct ItemTests {{
    @Test("Item initializes with correct default state")
    func itemDefaults() {{
        let item = Item(name: "Test")
        #expect(item.isComplete == false)
    }}

    @Test("Throws on invalid input", arguments: ["", "   "])
    func invalidNames(name: String) {{
        #expect(throws: Item.ValidationError.self) {{
            try Item.validate(name: name)
        }}
    }}
}}
"""


def ui_tests_swift(app_name: str) -> str:
    return f"""
import XCTest

final class {app_name}UITests: XCTestCase {{
    override func setUpWithError() throws {{
        continueAfterFailure = false
    }}

    func testAppLaunches() throws {{
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.windows.firstMatch.waitForExistence(timeout: 5))
    }}
}}
"""


def entitlements_plist() -> str:
    return """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.app-sandbox</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-only</key>
    <true/>
</dict>
</plist>
"""


# --------------------------------------------------------------------------
# Tooling config templates
# --------------------------------------------------------------------------


def xcodegen_project_yml(app_name: str, bundle_id: str) -> str:
    return f"""
name: {app_name}
options:
  bundleIdPrefix: {bundle_id.rsplit(".", 1)[0]}
  deploymentTarget:
    macOS: "14.0"
  createIntermediateGroups: true

packages:
  SwiftLintPlugin:
    url: https://github.com/realm/SwiftLint
    from: 0.55.0

targets:
  {app_name}:
    type: application
    platform: macOS
    sources:
      - path: {app_name}
    resources:
      - path: {app_name}/Resources/Assets.xcassets
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: {bundle_id}
        MACOSX_DEPLOYMENT_TARGET: "14.0"
        SWIFT_VERSION: "6.0"
        ENABLE_HARDENED_RUNTIME: YES
        CODE_SIGN_ENTITLEMENTS: {app_name}/Resources/{app_name}.entitlements
    info:
      path: SupportingFiles/{app_name}.Info.plist
      properties:
        CFBundleDisplayName: {app_name}
        LSMinimumSystemVersion: "14.0"
    buildToolPlugins:
      - plugin: SwiftLintBuildToolPlugin
        package: SwiftLintPlugin

  {app_name}Tests:
    type: bundle.unit-test
    platform: macOS
    sources:
      - path: {app_name}Tests
    dependencies:
      - target: {app_name}
    settings:
      base:
        SWIFT_VERSION: "6.0"
        GENERATE_INFOPLIST_FILE: YES

  {app_name}UITests:
    type: bundle.ui-testing
    platform: macOS
    sources:
      - path: {app_name}UITests
    dependencies:
      - target: {app_name}
    settings:
      base:
        SWIFT_VERSION: "6.0"
        GENERATE_INFOPLIST_FILE: YES

schemes:
  {app_name}:
    build:
      targets:
        {app_name}: all
        {app_name}Tests: [test]
        {app_name}UITests: [test]
    test:
      targets:
        - {app_name}Tests
        - {app_name}UITests
    run:
      config: Debug
"""


def swiftlint_yml() -> str:
    return """
excluded:
  - .build
  - DerivedData
  - "**/.build"

opt_in_rules:
  - force_unwrapping
  - empty_count
  - closure_spacing
  - contains_over_first_not_nil

disabled_rules:
  - line_length
  - todo

# swift format (Apple's formatter) emits trailing commas in multiline
# collections per SE-0383, so tell SwiftLint to require them too; otherwise
# the formatter and linter fight each other on every commit.
trailing_comma:
  mandatory_comma: true

analyzer_rules:
  - unused_import
  - unused_declaration
"""


def swift_format_json() -> str:
    return """
{
  "version": 1,
  "lineLength": 120,
  "indentation": { "spaces": 4 },
  "tabWidth": 4,
  "respectsExistingLineBreaks": true,
  "lineBreakBeforeControlFlowKeywords": false,
  "lineBreakBeforeEachArgument": true
}
"""


def pre_commit_config_yml() -> str:
    return """
repos:
  - repo: local
    hooks:
      - id: swift-format
        name: swift format
        entry: swift format --in-place
        language: system
        files: \\.swift$
      - id: swiftlint
        name: swiftlint
        entry: swiftlint lint --strict --quiet
        language: system
        files: \\.swift$
        pass_filenames: false
"""


def github_actions_ci_yml(app_name: str) -> str:
    return f"""
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  quality-test:
    runs-on: macos-15
    steps:
      - uses: actions/checkout@v4

      - name: Select Xcode
        run: sudo xcode-select -s /Applications/Xcode_16.app

      - name: Install XcodeGen
        run: brew install xcodegen

      - name: Install SwiftLint
        run: brew install swiftlint

      - name: Install Periphery
        run: brew install periphery

      - name: Generate Xcode project
        run: xcodegen generate

      - name: Lint
        run: swiftlint lint --strict

      - name: Analyze with SwiftLint
        run: bash Scripts/swiftlint-analyze.sh

      - name: Find unused code
        run: periphery scan

      - name: Check formatting
        run: swift format lint --recursive {app_name}/ {app_name}Tests/ {app_name}UITests/

      - name: Run tests
        run: |
          xcodebuild test \\
            -project {app_name}.xcodeproj \\
            -scheme {app_name} \\
            -destination 'platform=macOS' \\
            -resultBundlePath TestResults

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: TestResults
"""


def makefile(app_name: str) -> str:
    return f"""
.PHONY: generate format lint analyze dead-code test build run precommit clean

generate:
\txcodegen generate

format:
\tswift format --in-place --recursive {app_name}/ {app_name}Tests/ {app_name}UITests/

lint:
\tswiftlint lint --strict

analyze:
\t@bash Scripts/swiftlint-analyze.sh

dead-code:
\tperiphery scan

test:
\txcodebuild test -project {app_name}.xcodeproj -scheme {app_name} -destination 'platform=macOS'

build:
\t@bash Scripts/build-app.sh

run: build
\t@open "Build/{app_name}.app"

precommit: format lint analyze dead-code test

clean:
\trm -rf {app_name}.xcodeproj DerivedData TestResults Build .build
"""


def build_app_sh(app_name: str, bundle_id: str) -> str:
    return f"""#!/bin/bash
set -euo pipefail

APP_NAME="{app_name}"
BUNDLE_ID="{bundle_id}"
CONFIGURATION="${{CONFIGURATION:-release}}"
BUILD_DIR=".build"
APP_BUNDLE="Build/$APP_NAME.app"

echo "==> Building $APP_NAME with SwiftPM ($CONFIGURATION)..."
swift build -c "$CONFIGURATION"

echo "==> Creating app bundle\u2026"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy the compiled binary
BIN_PATH=$(swift build -c "$CONFIGURATION" --show-bin-path)
cp "$BIN_PATH/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/"

# Generate Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Compile asset catalog if present and non-empty
if [ -d "$APP_NAME/Resources/Assets.xcassets" ] && [ "$(ls -A "$APP_NAME/Resources/Assets.xcassets" 2>/dev/null)" ]; then
    echo "==> Compiling asset catalog\u2026"
    xcrun actool "$APP_NAME/Resources/Assets.xcassets" \\
        --compile "$APP_BUNDLE/Contents/Resources" \\
        --platform macosx \\
        --minimum-deployment-target 14.0
fi

# Copy remaining resources (excluding .xcassets which was compiled)
if [ -d "$APP_NAME/Resources" ]; then
    rsync -a --exclude="Assets.xcassets" --exclude="*.entitlements" \\
        "$APP_NAME/Resources/" "$APP_BUNDLE/Contents/Resources/" 2>/dev/null || true
fi

echo ""
echo "App bundle created at: $APP_BUNDLE"
"""


def swiftlint_analyze_sh(app_name: str) -> str:
    return f"""#!/bin/bash
set -euo pipefail

APP_NAME="{app_name}"
DERIVED_DATA_PATH="DerivedData/SwiftLintAnalyze"
BUILD_LOG="$DERIVED_DATA_PATH/xcodebuild.log"

# Analyzer rules need a clean, full compiler invocation. SwiftLint consumes
# the Xcode build log, so generate the project and build it entirely by CLI.
xcodegen generate
rm -rf "$DERIVED_DATA_PATH"
mkdir -p "$DERIVED_DATA_PATH"
xcodebuild test \
    -project "$APP_NAME.xcodeproj" \
    -scheme "$APP_NAME" \
    -destination 'platform=macOS' \
    -derivedDataPath "$DERIVED_DATA_PATH" \
    -skipPackagePluginValidation \
    -skipMacroValidation \
    2>&1 | tee "$BUILD_LOG"

swiftlint analyze --strict --compiler-log-path "$BUILD_LOG"
"""


def periphery_yml() -> str:
    return """
# Finds unused code (dead types, functions, properties) across the whole
# target graph — something SwiftLint can't do on its own.
# Run with: periphery scan --config .periphery.yml
disable_update_check: true
"""


def license_mit(app_name: str) -> str:
    year = datetime.date.today().year
    return f"""MIT License

Copyright (c) {year} The {app_name} Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def package_swift(app_name: str) -> str:
    return f"""
// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "{app_name}",
    platforms: [
        .macOS(.v14)
    ],
    targets: [
        .executableTarget(
            name: "{app_name}",
            path: "{app_name}",
            resources: [.process("Resources")]
        ),
        .testTarget(
            name: "{app_name}Tests",
            dependencies: ["{app_name}"],
            path: "{app_name}Tests"
        )
    ]
)
"""


def gitignore() -> str:
    return """
.DS_Store
.build/
Build/
DerivedData/
TestResults/
SupportingFiles/
*.xcodeproj
xcuserdata/
.swiftpm/
"""


def readme_md(app_name: str) -> str:
    return f"""
# {app_name}

Modern SwiftUI macOS app, scaffolded with a feature-based layout and
lint/format/test automation wired up from the start.

## Quick start (SPM)

Build and run without ever opening Xcode:

```bash
make build       # compile with SwiftPM + create .app bundle
make run         # build (if needed) and launch the app
```

Or step by step with SwiftPM directly:

```bash
swift build -c release                              # compile
bash Scripts/build-app.sh                            # create .app bundle
open "Build/{app_name}.app"                          # launch it
```

## First-time setup

Install the command-line tooling:

```bash
brew install swiftlint periphery pre-commit
pre-commit install
```

XcodeGen is only needed for the XCTest UI-test target, the SwiftLint analyzer
check, or if you want an Xcode project. It can be used entirely from the
command line:

```bash
brew install xcodegen
xcodegen generate
open {app_name}.xcodeproj  # optional
```

## Common tasks

```bash
make build       # compile with SwiftPM + create .app bundle
make run         # build and launch the app
make format      # auto-format all Swift files
make lint        # run SwiftLint syntax rules (--strict)
make analyze     # run SwiftLint analyzer rules after a clean full compile
make dead-code   # scan every SwiftPM target for unused declarations (Periphery)
make test        # run unit + UI tests (requires xcodegen generate first)
make precommit   # format + lint + analysis + dead-code + test
```

## How it works

This project uses **two build systems** side by side:

| System | Manifest | Purpose |
|---|---|---|
| **SwiftPM** | `Package.swift` | Compile sources, run unit tests, produce executable |
| **XcodeGen** | `project.yml` | Generate `.xcodeproj` for UI tests, full Xcode integration |

A `Scripts/build-app.sh` script wraps `swift build` and assembles the
compiled binary into a proper `.app` bundle with `Info.plist`, compiled
asset catalogs, and resources \u2014 no Xcode required.

## Code quality

Regular SwiftLint rules run quickly from source with `make lint`. The
`unused_import` and `unused_declaration` analyzer rules require a clean,
full compile, so `make analyze` generates the Xcode project and captures an
`xcodebuild` compiler log before running `swiftlint analyze`. It never
requires the Xcode UI.

`make dead-code` runs Periphery. Periphery reads `Package.swift`, builds all
SwiftPM targets (including unit tests), and traverses their declaration graph
to find unused classes, functions, properties, and other declarations.

## Structure

```
{app_name}/
├── App/            # App entry point, AppState
├── Features/        # Feature-scoped views/view models
├── Models/          # Data models
├── Services/        # Persistence, networking, etc.
├── DesignSystem/     # Shared colors, components
└── Resources/        # Assets, Info.plist, entitlements
{app_name}Tests/       # Swift Testing unit tests
{app_name}UITests/     # XCTest UI tests
Scripts/
├── build-app.sh              # macOS .app bundle builder (SPM-based)
└── swiftlint-analyze.sh      # clean Xcode CLI build + SwiftLint analyzer rules
.periphery.yml                # Periphery dead-code scan configuration
```

CI (`.github/workflows/ci.yml`) regenerates the Xcode project with XcodeGen,
then runs regular SwiftLint, compiled SwiftLint analyzer rules, Periphery,
a `swift format` check, and the full test suite on every PR.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
"""


# --------------------------------------------------------------------------
# Scaffolding
# --------------------------------------------------------------------------


def build_project(root: Path, app_name: str, bundle_id: str):
    app_dir = root / app_name

    # App entry + state
    write_file(app_dir / "App" / f"{app_name}App.swift", app_entry_swift(app_name))
    write_file(app_dir / "App" / "AppState.swift", app_state_swift())

    # Features
    write_file(
        app_dir / "Features" / "Settings" / "SettingsView.swift", settings_view_swift()
    )
    write_file(
        app_dir / "Features" / "Settings" / "SettingsViewModel.swift",
        settings_view_model_swift(),
    )
    touch_gitkeep(app_dir / "Features" / "Sidebar")
    touch_gitkeep(app_dir / "Features" / "Detail")
    write_file(app_dir / "ContentView.swift", content_view_swift())

    # Models / Services / DesignSystem
    write_file(app_dir / "Models" / "Item.swift", item_model_swift())
    write_file(
        app_dir / "Services" / "PersistenceController.swift",
        persistence_controller_swift(app_name),
    )
    write_file(app_dir / "DesignSystem" / "Colors.swift", colors_swift())

    # Resources
    write_file(app_dir / "Resources" / f"{app_name}.entitlements", entitlements_plist())
    touch_gitkeep(app_dir / "Resources" / "Assets.xcassets")

    # Tests
    write_file(
        root / f"{app_name}Tests" / "ItemTests.swift", item_tests_swift(app_name)
    )
    write_file(
        root / f"{app_name}UITests" / f"{app_name}UITests.swift",
        ui_tests_swift(app_name),
    )

    # SPM integration
    write_file(root / "Package.swift", package_swift(app_name))

    # Build script for .app bundle (SPM-based)
    script_path = root / "Scripts" / "build-app.sh"
    write_file(script_path, build_app_sh(app_name, bundle_id))
    script_path.chmod(0o755)
    logging.info(f"chmod +x {script_path}")

    # Full-compile SwiftLint analyzer-rule check (Xcode CLI-based)
    analyzer_script_path = root / "Scripts" / "swiftlint-analyze.sh"
    write_file(analyzer_script_path, swiftlint_analyze_sh(app_name))
    analyzer_script_path.chmod(0o755)
    logging.info(f"chmod +x {analyzer_script_path}")

    # Tooling / config
    write_file(root / "project.yml", xcodegen_project_yml(app_name, bundle_id))
    write_file(root / ".swiftlint.yml", swiftlint_yml())
    write_file(root / ".periphery.yml", periphery_yml())
    write_file(root / ".swift-format", swift_format_json())
    write_file(root / ".pre-commit-config.yaml", pre_commit_config_yml())
    write_file(
        root / ".github" / "workflows" / "ci.yml", github_actions_ci_yml(app_name)
    )
    write_file(root / "Makefile", makefile(app_name))
    write_file(root / ".gitignore", gitignore())
    write_file(root / "LICENSE", license_mit(app_name))
    write_file(root / "README.md", readme_md(app_name))


def main(args):
    app_name = args.app_name
    bundle_id = args.bundle_id or f"com.example.{app_name.lower()}"
    output_dir = Path(args.output_dir).expanduser().resolve()
    root = output_dir / app_name

    if root.exists():
        if args.overwrite:
            logging.info(f"removing existing directory {root}")
            shutil.rmtree(root)
        else:
            logging.error(f"{root} already exists. Use --overwrite to replace it.")
            sys.exit(1)

    logging.info(f"scaffolding {app_name} at {root} (bundle id: {bundle_id})")
    build_project(root, app_name, bundle_id)

    print(f"\nDone. Project created at: {root}\n")
    print("Next steps (SPM — no Xcode needed):")
    print(f"  cd {root}")
    print("  make build        # compile + create .app bundle")
    print("  make run          # build and launch the app")
    print("  swift test        # run unit tests via SwiftPM")
    print("  brew install swiftlint periphery  # enable code-quality checks")
    print("  make analyze      # run full-compile SwiftLint analyzer rules")
    print("  make dead-code    # scan all SwiftPM targets with Periphery")
    print()
    print("Or with Xcode:")
    print("  brew install xcodegen pre-commit   # if not already installed")
    print("  xcodegen generate")
    print(f"  open {app_name}.xcodeproj")
    print("  pre-commit install")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
