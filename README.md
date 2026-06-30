# TWL400 — Using AI to Secure the Modern SOC (Module 3 Hands-On Lab)

This repository contains the **Module 3 hands-on lab** — *Cross-Layer Attack Lab (End-to-End)* — for the Microsoft L300/L400 TechWorkshop **Using AI to Secure the Modern SOC**.

Learners take the role of a security Cloud Solution Architect advising **Zava**, whose SOC is buried in alert noise. In one continuous incident they scope a coordinated, AI-driven attack that crosses identity, AI, data, infrastructure, and endpoint; reconstruct the lifecycle; execute a coordinated automated response; and assemble the module's **Proof Through Scenario** executive deliverable — using Microsoft Security Copilot, Defender XDR, Microsoft Sentinel, Microsoft Entra, and Microsoft Defender for Cloud — AI threat protection.

The lab is published as a GitHub Pages site. Instructional content lives under [`docs/`](docs/), with image assets under [`media/`](media/).

> **Draft status:** This is a full first draft authored from the lab outline ahead of the lab tenant build. Portal navigation, KQL, Security Copilot prompts, and the seeded entities are **illustrative** and will be validated against the provisioned environment during the build. See [`AGENTS.md`](AGENTS.md) for the lab canon and authoring conventions.

## Build the site locally

This is a [Jekyll](https://jekyllrb.com/) site using the [just-the-docs](https://just-the-docs.com/) theme. Ruby 3.x is required (see `.devcontainer/` for a ready-made environment).

```bash
bundle install
bundle exec jekyll serve
```

Then browse to `http://localhost:4000`.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
