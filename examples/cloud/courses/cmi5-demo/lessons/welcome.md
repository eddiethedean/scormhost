# cmi5 Demo (example)

This is the **Security Awareness** sample course, configured to demonstrate **cmi5 packaging** (an LMS‑friendly profile of xAPI).

## What you’re looking at

- A normal LXPack course (Markdown + HTML interaction + YAML quiz)
- `lxpack.config.json` sets `defaultTarget` to **cmi5**
- The build outputs a cmi5 package with `cmi5.xml` and activity structure

## How to use it

- Run `lxpack preview` to iterate quickly
- Run `lxpack build` to generate a cmi5 package
- Import into a cmi5‑capable LMS (launch-time parameters supply LRS credentials)
