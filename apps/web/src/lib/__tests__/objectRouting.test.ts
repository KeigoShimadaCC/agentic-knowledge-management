import { objectKindLabel, objectRoute } from "@/lib/objectRouting";

describe("objectRoute", () => {
  it.each([
    ["page", "abc", "/app/pages/abc"],
    ["source", "def", "/app/sources/def"],
    ["chat", "ghi", "/app/chats/ghi"],
    ["asset", "jkl", "/app/assets"],
    ["claim", "mno", "/app"],
    ["task", "pqr", "/app"],
    ["unknown", "stu", "/app"],
  ])("routes %s objects", (kind, id, expected) => {
    expect(objectRoute(kind, id)).toBe(expected);
  });
});

describe("objectKindLabel", () => {
  it("capitalizes the object kind", () => {
    expect(objectKindLabel("source")).toBe("Source");
  });
});
