import Foundation
@testable import KnowledgeOS

enum FixtureLoader {
    static func data(named name: String) throws -> Data {
        let bundle = Bundle(for: BundleMarker.self)
        guard let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "Fixtures")
            ?? bundle.url(forResource: name, withExtension: "json") else {
            throw NSError(domain: "FixtureLoader", code: 1, userInfo: [NSLocalizedDescriptionKey: "Missing fixture \(name).json"])
        }
        return try Data(contentsOf: url)
    }

    static func decode<T: Decodable>(_ type: T.Type, named name: String) throws -> T {
        try JSONCoding.decoder.decode(type, from: data(named: name))
    }
}

private final class BundleMarker {}
