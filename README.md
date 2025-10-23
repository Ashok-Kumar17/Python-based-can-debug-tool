# Infinity

## Overview

**Infinity** is a project I worked on during my internship at **Ather Energy** (Summer 2025).  
The project involved building and integrating software tools for internal testing and automation within Ather’s embedded systems ecosystem.

During this work, I focused on firmware development, debugging, and creating scalable software modules that interact seamlessly with hardware-level components.  
The repository serves as a base framework to organize and scale features for internal development and testing.

---

## My Role & Contributions

I contributed to the following areas:
- Designed and implemented key firmware modules in **C/C++** for hardware communication.
- Developed automation scripts and debug tools using **Python** for data logging and validation.
- Integrated GitLab CI/CD pipelines for build verification and deployment within Ather’s ecosystem.
- Collaborated closely with the Embedded Software and Validation teams to ensure robustness and reliability of releases.

---

## Tech Stack

- **Languages:** C, C++, Python  
- **Frameworks/Tools:** ESP-IDF, PlatformIO, GitLab CI/CD, CAN/TWAI, UART communication  
- **Version Control:** Git (GitLab-based workflow)  
- **Platforms:** ESP32-based embedded systems

---

## Repository Structure


infinity/
├─ firmware/ # Embedded code and modules
├─ tools/ # Python scripts for automation and logging
├─ tests/ # Unit and integration test scripts
├─ docs/ # Internal technical documentation
└─ .gitlab-ci.yml # CI/CD pipeline configuration


---

## Getting Started

To clone and work with this repository:

```bash
git clone https://gitlab.atherengineering.in/sharan.ap/infinity.git
cd infinity
```

If this is your first time setting up:

Install required dependencies (Python 3.10+, ESP-IDF v5.x)

Build the firmware:
```bash
idf.py build
```
Run tests locally:
```bash
pytest
```
Key Features

Modular design for embedded-software scalability.

Integrated CI pipeline for automated testing.

Hardware abstraction layers to ensure compatibility across ESP-based boards.

Built-in data logging and debug utilities for sensor and communication validation.

Collaboration & Workflow

This project was developed collaboratively within the Ather Engineering team.
We followed an Agile development workflow with:

Merge requests for code review,

Issue tracking for task breakdowns,

Continuous Integration for quality assurance,

Regular testing and validation on target hardware.

Learnings & Takeaways

Working on Infinity deepened my understanding of:

End-to-end software-hardware integration in production environments,

Structuring scalable embedded systems repositories,

Best practices in CI/CD and code review,

Collaborative version control in large engineering teams.

This experience also strengthened my transition path from Embedded Systems Engineering to Software Development & AI/ML, helping me understand how low-level systems interact with high-level software intelligence.

License

Internal Ather repository (proprietary).
This README is for demonstration and portfolio purposes only.

Author

Ashok Kumar Meena
Electrical Engineering, IIT Madras
Embedded Systems & Software Engineer | Ather Energy ( ex Intern)

