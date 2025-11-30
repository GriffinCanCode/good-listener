// Package errors provides unified error handling using protobuf-defined ErrorCode.
// Error codes are defined in cognition.proto and shared across Python, Go, and TypeScript.
package errors

import (
	"fmt"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/anypb"

	"github.com/GriffinCanCode/good-listener/backend/platform/pkg/pb"
)

// grpcCodeMap maps protobuf ErrorCode to gRPC status codes.
var grpcCodeMap = map[pb.ErrorCode]codes.Code{
	pb.ErrorCode_ERROR_CODE_UNSPECIFIED:     codes.Unknown,
	pb.ErrorCode_UNKNOWN:                    codes.Unknown,
	pb.ErrorCode_INTERNAL:                   codes.Internal,
	pb.ErrorCode_INVALID_ARGUMENT:           codes.InvalidArgument,
	pb.ErrorCode_NOT_FOUND:                  codes.NotFound,
	pb.ErrorCode_UNAVAILABLE:                codes.Unavailable,
	pb.ErrorCode_TIMEOUT:                    codes.DeadlineExceeded,
	pb.ErrorCode_CANCELLED:                  codes.Canceled,
	pb.ErrorCode_AUDIO_INVALID_FORMAT:       codes.InvalidArgument,
	pb.ErrorCode_AUDIO_EMPTY_INPUT:          codes.InvalidArgument,
	pb.ErrorCode_AUDIO_TRANSCRIPTION_FAILED: codes.Internal,
	pb.ErrorCode_AUDIO_VAD_FAILED:           codes.Internal,
	pb.ErrorCode_AUDIO_DIARIZATION_FAILED:   codes.Internal,
	pb.ErrorCode_AUDIO_MODEL_LOAD_FAILED:    codes.Unavailable,
	pb.ErrorCode_LLM_NOT_CONFIGURED:         codes.FailedPrecondition,
	pb.ErrorCode_LLM_API_ERROR:              codes.Internal,
	pb.ErrorCode_LLM_RATE_LIMITED:           codes.ResourceExhausted,
	pb.ErrorCode_LLM_CONTEXT_TOO_LONG:       codes.InvalidArgument,
	pb.ErrorCode_LLM_INVALID_RESPONSE:       codes.Internal,
	pb.ErrorCode_MEMORY_STORE_FAILED:        codes.Internal,
	pb.ErrorCode_MEMORY_QUERY_FAILED:        codes.Internal,
	pb.ErrorCode_MEMORY_POOL_EXHAUSTED:      codes.ResourceExhausted,
	pb.ErrorCode_MEMORY_INIT_FAILED:         codes.Unavailable,
	pb.ErrorCode_OCR_INIT_FAILED:            codes.Unavailable,
	pb.ErrorCode_OCR_EXTRACT_FAILED:         codes.Internal,
	pb.ErrorCode_OCR_INVALID_IMAGE:          codes.InvalidArgument,
	pb.ErrorCode_CONFIG_INVALID:             codes.InvalidArgument,
	pb.ErrorCode_CONFIG_MISSING:             codes.FailedPrecondition,
}

// AppError is the base error type with structured error code and metadata.
type AppError struct {
	Code     pb.ErrorCode
	Message  string
	Metadata map[string]string
	Cause    error
}

// Error implements the error interface.
func (e *AppError) Error() string {
	s := fmt.Sprintf("[%s] %s", e.Code.String(), e.Message)
	if len(e.Metadata) > 0 {
		s += fmt.Sprintf(" %v", e.Metadata)
	}
	if e.Cause != nil {
		s += fmt.Sprintf(" caused by: %v", e.Cause)
	}
	return s
}

// Unwrap returns the underlying cause for errors.Is/As.
func (e *AppError) Unwrap() error { return e.Cause }

// GRPCCode returns the corresponding gRPC status code.
func (e *AppError) GRPCCode() codes.Code {
	if c, ok := grpcCodeMap[e.Code]; ok {
		return c
	}
	return codes.Unknown
}

// ToProto converts to protobuf ErrorDetail message.
func (e *AppError) ToProto() *pb.ErrorDetail {
	detail := &pb.ErrorDetail{Code: e.Code, Message: e.Message}
	if len(e.Metadata) > 0 {
		detail.Metadata = e.Metadata
	}
	return detail
}

// GRPCStatus returns a gRPC status with the ErrorDetail attached.
func (e *AppError) GRPCStatus() *status.Status {
	st := status.New(e.GRPCCode(), e.Error())
	detail, _ := anypb.New(e.ToProto())
	st, _ = st.WithDetails(detail)
	return st
}

// New creates a new AppError with the given code and message.
func New(code pb.ErrorCode, msg string) *AppError {
	return &AppError{Code: code, Message: msg}
}

// Newf creates a new AppError with formatted message.
func Newf(code pb.ErrorCode, format string, args ...interface{}) *AppError {
	return &AppError{Code: code, Message: fmt.Sprintf(format, args...)}
}

// Wrap wraps an existing error with an AppError.
func Wrap(err error, code pb.ErrorCode, msg string) *AppError {
	return &AppError{Code: code, Message: msg, Cause: err}
}

// Wrapf wraps an existing error with formatted message.
func Wrapf(err error, code pb.ErrorCode, format string, args ...interface{}) *AppError {
	return &AppError{Code: code, Message: fmt.Sprintf(format, args...), Cause: err}
}

// WithMetadata adds metadata to an AppError.
func (e *AppError) WithMetadata(key, value string) *AppError {
	if e.Metadata == nil {
		e.Metadata = make(map[string]string)
	}
	e.Metadata[key] = value
	return e
}

// FromGRPCError extracts AppError from a gRPC error if present.
func FromGRPCError(err error) *AppError {
	st, ok := status.FromError(err)
	if !ok {
		return &AppError{Code: pb.ErrorCode_UNKNOWN, Message: err.Error(), Cause: err}
	}

	// Try to extract ErrorDetail from status details
	for _, detail := range st.Details() {
		if any, ok := detail.(*anypb.Any); ok {
			var errDetail pb.ErrorDetail
			if err := any.UnmarshalTo(&errDetail); err == nil {
				return &AppError{
					Code:     errDetail.Code,
					Message:  errDetail.Message,
					Metadata: errDetail.Metadata,
				}
			}
		}
		// Try direct type assertion
		if ed, ok := detail.(*pb.ErrorDetail); ok {
			return &AppError{Code: ed.Code, Message: ed.Message, Metadata: ed.Metadata}
		}
	}

	// Fallback: map gRPC code to our error code
	return &AppError{Code: grpcToErrorCode(st.Code()), Message: st.Message()}
}

// grpcToErrorCode maps gRPC codes back to our error codes (best effort).
func grpcToErrorCode(c codes.Code) pb.ErrorCode {
	switch c {
	case codes.InvalidArgument:
		return pb.ErrorCode_INVALID_ARGUMENT
	case codes.NotFound:
		return pb.ErrorCode_NOT_FOUND
	case codes.Unavailable:
		return pb.ErrorCode_UNAVAILABLE
	case codes.DeadlineExceeded:
		return pb.ErrorCode_TIMEOUT
	case codes.Canceled:
		return pb.ErrorCode_CANCELLED
	case codes.Internal:
		return pb.ErrorCode_INTERNAL
	case codes.FailedPrecondition:
		return pb.ErrorCode_CONFIG_MISSING
	case codes.ResourceExhausted:
		return pb.ErrorCode_LLM_RATE_LIMITED
	default:
		return pb.ErrorCode_UNKNOWN
	}
}

// IsCode checks if an error has a specific error code.
func IsCode(err error, code pb.ErrorCode) bool {
	if appErr, ok := err.(*AppError); ok {
		return appErr.Code == code
	}
	return false
}

// IsRetryable returns true if the error is potentially retryable.
func IsRetryable(err error) bool {
	appErr, ok := err.(*AppError)
	if !ok {
		return false
	}
	switch appErr.Code {
	case pb.ErrorCode_UNAVAILABLE, pb.ErrorCode_TIMEOUT, pb.ErrorCode_LLM_RATE_LIMITED, pb.ErrorCode_MEMORY_POOL_EXHAUSTED:
		return true
	default:
		return false
	}
}

// Ensure AppError implements proto.Message for type assertions.
var _ proto.Message = (*pb.ErrorDetail)(nil)
