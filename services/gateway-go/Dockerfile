FROM golang:1.22-alpine AS build

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY cmd ./cmd

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /bin/gateway ./cmd/gateway

FROM alpine:3.20

RUN adduser -D app
USER app

COPY --from=build /bin/gateway /bin/gateway

EXPOSE 8080

CMD ["/bin/gateway"]
