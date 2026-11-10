# SP 03: Native app vs. mobile web

**Decision for Iteration 1:** build with **Expo (React Native + TypeScript)**. One codebase gives us iOS, Android and web, so this decision stays open. All analysis runs **on the server**, so the client is thin either way.

## Comparison for this use case

| Concern | Native (Expo on iOS/Android) | Mobile web (Expo web / browser) |
|---------|------------------------------|----------------------------------|
| Install friction at an expo | Needs Expo Go or a store/TestFlight build | None: scan a QR code (US 35) |
| Video recording | `expo-camera` `recordAsync` with `maxDuration`. Reliable | `expo-camera` **can't record video on web**. We use `<input type="file" accept="video/*" capture>`, which opens the phone's camera app. No in-app countdown or auto-stop |
| Camera permission UX | OS dialog. On denial we deep-link to Settings | Browser prompt. Can't deep-link to settings; we show instructions instead |
| Frame rate / resolution control | Better (camera props) | Up to the OS camera app |
| Live "golfer in frame" detection (future) | Possible with `react-native-vision-camera` frame processors (needs a dev build, not Expo Go) | Possible with MediaPipe JS (`@mediapipe/tasks-vision`) in the browser |
| Playing the overlay video | `expo-video`. Needs H.264 MP4 + HTTP Range | `<video>`. Same requirements |
| Older phones | Fine (processing is server-side) | Fine (processing is server-side) |
| Updates during the event | OTA via EAS Update | Instant (redeploy) |

## Recommendation (provisional)
- **Booth / expo host device:** native build. Best capture control (countdown, auto-stop, framing guide).
- **Visitors scanning a QR code (US 35):** web build of the same app. It uses the file-input capture fallback and the same backend.
- Revisit once SAS answers [open-questions.md](../open-questions.md) Q8 (target devices).

## Evidence to gather
- [ ] Record + upload round-trip time on an older Android phone (native vs. web)
- [ ] Check that the web fallback produces video the server can decode (iOS Safari HEVC `.mov`!)
- [ ] Overlay playback on iOS Safari and on Android Chrome
