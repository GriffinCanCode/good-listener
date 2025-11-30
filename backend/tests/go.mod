module github.com/GriffinCanCode/good-listener/backend/tests

go 1.24.0

require (
	github.com/GriffinCanCode/good-listener/backend/platform v0.0.0
	google.golang.org/grpc v1.75.0
)

replace github.com/GriffinCanCode/good-listener/backend/platform => ../platform

require (
	golang.org/x/net v0.46.0 // indirect
	golang.org/x/sys v0.37.0 // indirect
	golang.org/x/text v0.30.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20250818200422-3122310a409c // indirect
	google.golang.org/protobuf v1.36.10 // indirect
)
