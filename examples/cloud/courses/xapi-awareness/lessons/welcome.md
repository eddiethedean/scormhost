# xAPI Awareness (example)

This is the **Security Awareness** sample course, configured to demonstrate **xAPI export + runtime tracking**.

## What’s different in this example

- `tracking.xapi.activityIri` is set in `course.yaml`
- `lxpack.config.json` sets `defaultTarget` to **xapi**
- The runtime emits xAPI statements for key events (navigation, interactions, assessment)

## Try it

- Run `lxpack preview` and complete the lab + quiz
- Build `lxpack build` and inspect the package metadata (Tin Can / xAPI artifacts)

## Why it matters

xAPI packages are portable: the course can be launched with LRS credentials provided at launch time, and the runtime reports learner activity without hard‑coding secrets into the ZIP.
