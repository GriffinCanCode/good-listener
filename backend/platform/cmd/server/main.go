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

	"github.com/GriffinCanCode/good-listener/backend/platform/internal/config"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/grpcclient"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/orchestrator"
	"github.com/GriffinCanCode/good-listener/backend/platform/internal/server"
)

func main() {
	// Setup structured logging
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug}))
	slog.SetDefault(logger)

	cfg, err := config.Load()
	if err != nil {
		slog.Error("config validation failed", "error", err)
		os.Exit(1)
	}

	// Connect to inference gRPC server
	inference, err := grpcclient.New(cfg.Platform.InferenceAddr)
	if err != nil {
		slog.Error("failed to connect to inference server", "addr", cfg.Platform.InferenceAddr, "error", err)
		os.Exit(1)
	}
	defer func() { _ = inference.Close() }()

	// Wait for inference server to be ready before starting orchestrator
	startupCtx, startupCancel := context.WithCancel(context.Background())
	defer startupCancel()
	if err := inference.WaitReady(startupCtx, grpcclient.DefaultStartupTimeout); err != nil {
		slog.Error("inference server not ready", "error", err)
		os.Exit(1)
	}

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
		Addr:         cfg.Platform.HTTPAddr,
		Handler:      srv.Handler(),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		slog.Info("platform server starting", "http", cfg.Platform.HTTPAddr, "inference", cfg.Platform.InferenceAddr)
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
