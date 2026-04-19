import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPanel } from "../src/components/chat/ChatPanel";
import { sendRagFeedback } from "../src/lib/api";

const hookState = vi.hoisted(() => ({
  messages: [] as Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    questionHash?: string;
    cacheHit?: boolean;
    feedbackSent?: boolean;
  }>,
  status: "idle" as "idle" | "streaming" | "done" | "error",
  ask: vi.fn(),
  markFeedbackSent: vi.fn()
}));

vi.mock("../src/hooks/useRagStream", () => ({
  useRagStream: () => hookState
}));

vi.mock("../src/lib/api", async () => {
  const actual = await vi.importActual<typeof import("../src/lib/api")>("../src/lib/api");
  return {
    ...actual,
    sendRagFeedback: vi.fn().mockResolvedValue(undefined)
  };
});

describe("ChatPanel", () => {
  beforeEach(() => {
    hookState.messages = [];
    hookState.status = "idle";
    hookState.ask.mockReset();
    hookState.markFeedbackSent.mockReset();
    vi.mocked(sendRagFeedback).mockClear();
  });

  it("renders the empty assistant prompt", () => {
    render(<ChatPanel datasetHash="dataset-123" />);

    expect(screen.getByText(/Pergunte sobre KPIs/)).toBeInTheDocument();
  });

  it("sends feedback from visible assistant buttons", async () => {
    hookState.messages = [
      {
        id: "a1",
        role: "assistant",
        content: "Resposta cacheada.",
        questionHash: "abc123",
        cacheHit: true
      }
    ];

    render(<ChatPanel datasetHash="dataset-123" />);

    fireEvent.click(screen.getByRole("button", { name: "Útil" }));

    await waitFor(() => {
      expect(sendRagFeedback).toHaveBeenCalledWith("abc123", "up");
      expect(hookState.markFeedbackSent).toHaveBeenCalledWith("a1");
    });
    expect(screen.getByText("cache")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Não útil" })).toBeInTheDocument();
  });
});
