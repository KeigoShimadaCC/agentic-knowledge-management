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

## Local API Connection

The Connect screen defaults to `http://127.0.0.1:8001` on Simulator and checks:

```text
GET <baseURL>/api/v1/health
```

For a physical iPhone, use the networking profile from `docs/MOBILE_NETWORKING.md` after Phase PHONE-01B lands. This phase only ships the app-side health-check stub.

## App Transport Security

`KnowledgeOS/Resources/Info.plist` contains narrow HTTP exceptions for local development only:

- `127.0.0.1` for Simulator loopback
- `localhost` for local runs
- `NSAllowsLocalNetworking` for local private-network IPs such as `10.0.0.0/8`
- `local` with subdomains for mDNS LAN hostnames
- `ts.net` with subdomains for Tailscale MagicDNS

Plain IP CIDR ranges cannot be expressed as ATS domain exceptions, so the scaffold uses `NSAllowsLocalNetworking` for local private-network development without enabling `NSAllowsArbitraryLoads`. Remove these HTTP exceptions once a TLS-fronted mobile profile exists.
