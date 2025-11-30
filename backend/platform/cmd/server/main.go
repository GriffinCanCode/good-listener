// Platform server - orchestrates audio capture, screen capture, and WebSocket connections
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/good-listener/platform/internal/config"
	"github.com/good-listener/platform/internal/grpcclient"
	"github.com/good-listener/platform/internal/orchestrator"
	"github.com/good-listener/platform/internal/server"
)

func main() {
	// Setup structured logging
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug}))
	slog.SetDefault(logger)

	cfg := config.Load()

	// Connect to inference gRPC server
	inference, err := grpcclient.New(cfg.InferenceAddr)
	if err != nil {
		slog.Error("failed to connect to inference server", "addr", cfg.InferenceAddr, "error", err)
		os.Exit(1)
	}
	defer func() { _ = inference.Close() }()

	// Create orchestrator
	orch := orchestrator.New(inference, cfg)

	// Create HTTP/WebSocket server
	srv := server.New(orch, cfg)

	// Start orchestrator in background
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		if err := orch.Start(ctx); err != nil {
			slog.Error("orchestrator error", "error", err)
		}
	}()

	// Start HTTP server
	httpServer := &http.Server{
		Addr:         cfg.HTTPAddr,
		Handler:      srv.Handler(),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		slog.Info("platform server starting", "http", cfg.HTTPAddr, "inference", cfg.InferenceAddr)
		if err := httpServer.ListenAndServe(); err != http.ErrServerClosed {
			slog.Error("http server error", "error", err)
		}
	}()

	// Wait for shutdown signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	slog.Info("shutting down...")
	cancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("http shutdown error", "error", err)
	}

	orch.Stop()
	slog.Info("shutdown complete")
}
