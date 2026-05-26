# Wrap up

You just exercised three core pieces of LXPack authoring:

- **Variables**: an interaction set `path`
- **Flow**: the course routed you based on `path` and quiz completion
- **Tracking**: completion is enforced via the course `tracking.completion.threshold`

## Next steps

- Edit `interactions/choose-path/index.html` to set a different variable name/value.
- Add one more `flow` rule (for example, route to a “remediation” lesson on quiz fail).
- Try exporting with `lxpack build --target scorm12` to see the same behavior in an LMS.
