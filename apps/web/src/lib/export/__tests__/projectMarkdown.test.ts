import { projectToMarkdown } from "@/lib/export/projectMarkdown";
import { bulletSetFixture, projectFixture } from "@/components/projects/__tests__/fixtures";

describe("projectToMarkdown", () => {
  it("includes project basics", () => {
    const text = projectToMarkdown(projectFixture, [], []);

    expect(text).toContain("# KnowledgeOS v1");
    expect(text).toContain("Lead Engineer @ Acme");
    expect(text).toContain("python, nextjs");
  });

  it("includes bullet sets", () => {
    const text = projectToMarkdown(projectFixture, [bulletSetFixture], []);

    expect(text).toContain("## Resume Bullets");
    expect(text).toContain("Built a retrieval system");
  });
});
