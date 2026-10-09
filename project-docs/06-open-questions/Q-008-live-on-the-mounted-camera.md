# Q-008 · Never run live on the cart-mounted camera

- **Opened:** 2026-10-02 · **Status:** Open · **Priority:** high

Tested on a synthetic feed, on bag replay and in the sim. A live run with the
camera at its mount (and the cart moving) is still needed, including USB 3
bandwidth, sunlight and the IMU gravity prior under acceleration (low-pass
τ = 1 s; hard braking tilts it briefly; tilt tolerance 20°).
