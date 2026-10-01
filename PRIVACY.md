# Privacy Notes

ProctorVision AI processes webcam frames to identify configured electronic-device
classes. It is intended for controlled demonstrations and human-assisted review.

## Data handled

- Live webcam frames while monitoring is active
- Session start/end timestamps and status
- Confirmed incident device type, confidence, count and timing
- One annotated JPEG evidence image for each confirmed incident
- Per-session CSV exports generated on request

The application does not implement continuous video recording. Browser frames
are sent to the configured FastAPI server for inference and are not retained
unless they become the saved evidence frame for a confirmed incident.

## Deployment responsibilities

An operator deploying this project must define and communicate:

- The lawful purpose and participant consent process
- Who can view sessions and evidence
- How long records and images are retained
- How a participant can request access or deletion
- Where processing occurs and whether frames cross a network boundary
- How backups and exported CSV files are protected

Use synthetic or expressly approved evidence in public demonstrations. Never
commit the `data/` or `evidence/` directories to a public repository.

The system produces review flags, not misconduct decisions. A person should
evaluate context before any action is taken.
