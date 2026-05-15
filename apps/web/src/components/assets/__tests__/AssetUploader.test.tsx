import { fireEvent, screen } from "@testing-library/react";
import { AssetUploader } from "@/components/assets/AssetUploader";
import { renderWithProviders } from "@/test/render";

class MockXMLHttpRequest {
  static instances: MockXMLHttpRequest[] = [];

  upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  method = "";
  url = "";
  withCredentials = false;
  status = 201;
  responseText = JSON.stringify({
    object: { id: "object-1" },
    asset: { id: "asset-1" },
  });

  constructor() {
    MockXMLHttpRequest.instances.push(this);
  }

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  send() {
    this.upload.onprogress?.({ lengthComputable: true, loaded: 512, total: 1024 } as ProgressEvent);
  }
}

describe("AssetUploader", () => {
  beforeEach(() => {
    MockXMLHttpRequest.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXMLHttpRequest);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uploads a dropped file and renders progress", () => {
    const file = new File(["x".repeat(1024)], "sample.txt", { type: "text/plain" });

    renderWithProviders(<AssetUploader />, { withWorkspace: false });

    fireEvent.drop(screen.getByText(/Drop files here/i).closest("div") as HTMLElement, {
      dataTransfer: { files: [file] },
    });

    expect(MockXMLHttpRequest.instances).toHaveLength(1);
    const request = MockXMLHttpRequest.instances[0];
    expect(request?.method).toBe("POST");
    expect(request?.url).toBe("http://localhost:8000/api/v1/assets/upload");
    expect(request?.withCredentials).toBe(true);
    expect(screen.getByText("sample.txt")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });
});
