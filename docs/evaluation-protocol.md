# Controlled Evaluation Protocol

Use this protocol to measure progress without changing multiple thresholds at
once. Record every run, including failures.

## Test conditions

Record:

- Date and application commit/version
- Computer and CPU
- Runtime shown by the interface
- Browser and version
- Camera resolution
- Screen recorder on/off
- Lighting and approximate device distance
- Local or deployed backend and network type

Wait for **All clear** before beginning each device trial.

## Core cases

| Case | Scene | Expected result |
|---|---|---|
| N1 | Empty scene, 30 seconds | No confirmed incident |
| N2 | Book/notebook | No confirmed device |
| N3 | TV remote/control | No confirmed device |
| P1 | Vertical phone, front visible | Phone incident |
| P2 | Horizontal phone | Phone incident |
| P3 | Phone partially occluded | Record detected/missed |
| P4 | Phone at increasing distance | Record maximum reliable distance |
| L1 | Open laptop | Laptop incident |
| L2 | Thin laptop edge only | No laptop incident expected |
| T1 | Widescreen monitor/TV | TV/monitor incident |
| M1 | Phone and laptop together | Separate device-type incidents |
| R1 | Remove confirmed device | Resolve after configured clear delay |

Repeat each core case at least five times before reporting an accuracy rate.

## Measurements

For every trial, capture:

- Whether the expected class appeared
- Time to first bounding box
- Time to confirmed incident
- Peak confidence
- Interface round-trip latency
- Model inference latency
- Time from device removal to **All clear**
- Whether evidence was created
- Whether CSV and UI values agree

## Summary metrics

After labelling all trials, calculate:

- Recall = correct detections / positive trials
- False-positive rate = negative trials with an incident / negative trials
- Median and 95th-percentile confirmation time
- Median and 95th-percentile round-trip latency
- Evidence/CSV consistency rate

Do not describe confidence as accuracy. A displayed 91% confidence is the
model's score for that prediction, not evidence that the system is 91% accurate.

## Change discipline

1. Preserve the current configuration as the baseline.
2. Change only one threshold, model or transport setting.
3. Repeat the same labelled cases.
4. Compare both missed detections and false positives.
5. Keep the change only when the measured trade-off is acceptable.
