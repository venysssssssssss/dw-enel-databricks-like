import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatPanel } from "../src/components/chat/ChatPanel";

describe("ChatPanel", () => {
  it("renders the empty assistant prompt", () => {
    render(<ChatPanel datasetHash="dataset-123" />);

    expect(screen.getByText(/Pergunte sobre KPIs/)).toBeInTheDocument();
  });
});
