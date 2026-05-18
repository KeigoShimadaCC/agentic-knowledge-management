# KnowledgeOS iOS

Native SwiftUI scaffold for the private KnowledgeOS iPhone client.

## Prerequisites

- Xcode 16+
- XcodeGen: `brew install xcodegen`

## Generate and Build

```bash
cd apps/ios
xcodegen generate
xcodebuild -project KnowledgeOS.xcodeproj -scheme KnowledgeOS -destination 'platform=iOS Simulator,name=iPhone 16' build test
```

Do not hand-edit `KnowledgeOS.xcodeproj`. It is generated from `project.yml` and is intentionally ignored by Git.

Regenerate the project after any `project.yml` change:

```bash
cd apps/ios
xcodegen generate
```

## Private Device Install

PHONE-06 uses direct Xcode installation for private use. The bundle identifier is
`com.knowledgeos.ios`, and `project.yml` uses automatic signing without a committed
Apple Team ID.

1. Open `apps/ios/KnowledgeOS.xcodeproj` in Xcode after running `xcodegen generate`.
2. In Xcode, select the `KnowledgeOS` project, then the `KnowledgeOS` app target.
3. Open **Signing & Capabilities**.
4. Enable **Automatically manage signing** if it is not already enabled.
5. Select your Apple ID **Personal Team** from the Team menu.
6. Connect the iPhone by USB or use Xcode's paired wireless device support.
7. Select the physical iPhone as the run destination.
8. Press **Run**. Xcode builds, signs, installs, and launches the app.

If iOS blocks the first launch, trust the developer profile on the phone under
**Settings → General → VPN & Device Management**, then launch the app again.

## Device Base URL

Simulator can use `http://127.0.0.1:8001`. A physical iPhone cannot use Mac loopback, so
choose one of these profiles before logging in:

- **LAN:** use the Mac's private LAN address, for example `http://192.168.1.23:8001`.
  The phone and Mac must be on the same network, and the Mac firewall must allow the API port.
- **Tailscale:** use the Mac's MagicDNS name or Tailscale IP, for example
  `http://your-mac.tailnet-name.ts.net:8001`. This is the preferred profile when LAN
  discovery or cafe/office Wi-Fi isolation gets in the way.

The backend must be reachable from the phone at:

```text
GET <baseURL>/api/v1/health
```

Keep the selected base URL visible in Settings and switch profiles when moving between LAN
and Tailscale networks.

## Personal Team Recovery

Free Apple ID Personal Team development certificates are short-lived. Expect a reinstall about
every 7 days.

1. Connect or pair the iPhone with Xcode.
2. Re-run `xcodegen generate` if `project.yml` changed.
3. Open `KnowledgeOS.xcodeproj`.
4. Confirm the `KnowledgeOS` target still uses **Automatically manage signing** and your
   Personal Team.
5. Select the physical iPhone and press **Run**.
6. If the app was removed or expired, let Xcode reinstall it.
7. If iOS reports an untrusted developer again, trust the profile in Settings.
8. Recheck the base URL, then run the real-device smoke flow.

If signing fails after certificate expiry, remove stale provisioning profiles in Xcode
**Settings → Accounts → Manage Certificates**, then let Xcode recreate a development
certificate by running the app again.

## Optional TestFlight

Defer TestFlight unless multi-tester distribution is needed. Direct Xcode install is the
PHONE-06 path for a private single-user device. TestFlight would require an Apple Developer
Program membership, App Store Connect setup, build upload, and beta review.

## Local API Connection

The Connect screen defaults to `http://127.0.0.1:8001` on Simulator and checks:

```text
GET <baseURL>/api/v1/health
```

For a physical iPhone, use a LAN or Tailscale profile from `docs/MOBILE_NETWORKING.md`.

## App Transport Security

`KnowledgeOS/Resources/Info.plist` contains narrow HTTP exceptions for local development only:

- `127.0.0.1` for Simulator loopback
- `localhost` for local runs
- `NSAllowsLocalNetworking` for local private-network IPs such as `10.0.0.0/8`
- `local` with subdomains for mDNS LAN hostnames
- `ts.net` with subdomains for Tailscale MagicDNS

Plain IP CIDR ranges cannot be expressed as ATS domain exceptions, so the scaffold uses `NSAllowsLocalNetworking` for local private-network development without enabling `NSAllowsArbitraryLoads`. Remove these HTTP exceptions once a TLS-fronted mobile profile exists.
