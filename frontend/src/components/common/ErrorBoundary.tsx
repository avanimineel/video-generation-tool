import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-950/30 border border-red-800/50 rounded-xl m-2 text-xs text-red-200 space-y-3">
          <div className="flex items-center gap-2 font-semibold text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{this.props.fallbackTitle || "Panel Recovery"}</span>
          </div>
          <p className="text-[11px] text-neutral-300">
            {this.state.error?.message || "An unexpected error occurred in this view."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs flex items-center gap-1.5 transition-colors border border-white/10"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Reset Panel</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
