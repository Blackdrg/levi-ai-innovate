# backend/kernel/Dockerfile
FROM rust:1.75-slim as builder

WORKDIR /app
COPY . .

# Build the Axum-based HAL-0 service
RUN cargo build --release

# --- Runtime Stage ---
FROM debian:bookworm-slim

WORKDIR /app
COPY --from=builder /app/target/release/levi_kernel /app/hal0-service

EXPOSE 8001

CMD ["./hal0-service"]
