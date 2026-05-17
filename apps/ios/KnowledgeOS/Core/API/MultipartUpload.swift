import Foundation

struct MultipartUpload {
    let boundary: String
    let body: Data
    let contentType: String

    init(filename: String, mimeType: String, fileData: Data, fieldName: String = "file") {
        let boundary = "Boundary-\(UUID().uuidString)"
        var data = Data()
        let lineBreak = "\r\n"

        data.append("--\(boundary)\(lineBreak)")
        data.append("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(filename)\"\(lineBreak)")
        data.append("Content-Type: \(mimeType)\(lineBreak)\(lineBreak)")
        data.append(fileData)
        data.append(lineBreak)
        data.append("--\(boundary)--\(lineBreak)")

        self.boundary = boundary
        self.body = data
        self.contentType = "multipart/form-data; boundary=\(boundary)"
    }
}

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
