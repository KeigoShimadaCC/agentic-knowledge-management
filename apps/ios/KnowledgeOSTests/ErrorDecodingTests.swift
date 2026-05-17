import XCTest
@testable import KnowledgeOS

final class ErrorDecodingTests: XCTestCase {
    func testUnauthenticated401() throws {
        let data = try FixtureLoader.data(named: "error_unauthenticated")
        let error = APIError.from(httpStatus: 401, data: data)
        XCTAssertEqual(error, .notAuthenticated)
    }

    func testAIDisabled503() {
        let data = #"{"detail":"AI disabled","code":"ai_disabled"}"#.data(using: .utf8)!
        let error = APIError.from(httpStatus: 503, data: data)
        XCTAssertEqual(error, .aiDisabled)
    }

    func testValidation400() {
        let data = #"{"detail":"Invalid email","code":"validation_error"}"#.data(using: .utf8)!
        let error = APIError.from(httpStatus: 400, data: data)
        XCTAssertEqual(error, .validation("Invalid email"))
    }

    func testMissingCodeFallsBackToDetail() {
        let data = #"{"detail":"Something went wrong"}"#.data(using: .utf8)!
        let error = APIError.from(httpStatus: 400, data: data)
        XCTAssertEqual(error, .validation("Something went wrong"))
    }
}
