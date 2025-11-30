// Package trace - gRPC interceptors for trace propagation.
package trace

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
)

// UnaryClientInterceptor injects trace context into outgoing gRPC calls.
func UnaryClientInterceptor() grpc.UnaryClientInterceptor {
	return func(ctx context.Context, method string, req, reply any, cc *grpc.ClientConn, invoker grpc.UnaryInvoker, opts ...grpc.CallOption) error {
		ctx = injectMetadata(ctx)
		return invoker(ctx, method, req, reply, cc, opts...)
	}
}

// StreamClientInterceptor injects trace context into streaming gRPC calls.
func StreamClientInterceptor() grpc.StreamClientInterceptor {
	return func(ctx context.Context, desc *grpc.StreamDesc, cc *grpc.ClientConn, method string, streamer grpc.Streamer, opts ...grpc.CallOption) (grpc.ClientStream, error) {
		ctx = injectMetadata(ctx)
		return streamer(ctx, desc, cc, method, opts...)
	}
}

// injectMetadata adds trace context to outgoing gRPC metadata.
func injectMetadata(ctx context.Context) context.Context {
	tc, ok := FromContext(ctx)
	if !ok {
		tc = New()
		ctx = WithContext(ctx, tc)
	}

	md, ok := metadata.FromOutgoingContext(ctx)
	if !ok {
		md = metadata.New(nil)
	} else {
		md = md.Copy()
	}

	md.Set(TraceIDKey, tc.TraceID)
	md.Set(SpanIDKey, tc.SpanID)
	if tc.ParentSpanID != "" {
		md.Set(ParentSpanIDKey, tc.ParentSpanID)
	}

	return metadata.NewOutgoingContext(ctx, md)
}
