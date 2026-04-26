# Reachy Mini Personal Assistant

## Project Overview

The goal of this project was to create a personal assistant using the Reachy Mini robot. The assistant is designed to interact with users through voice commands and provide various services, such as answering questions, controlling smart home devices, and providing information.

To reduce the scope of the initial project, I focused on implementing the following:
- Face tracking: The robot can detect and track faces using its camera, allowing it to maintain eye contact with the user.
- Cron Job Support: The assistant will need to build some knowledge and gather information over time.  To support this, I implemented a cron job type system.  The initial cron jobs scrape calendars(gatech calendar, and create-x) and pulls the 25 new security papers from arxiv.

```mermaid
    C4Context
      title System Context diagram for Personal Assistant

      System_Boundary(reachy_system, "Reachy Mini System") {
        System(assistant, "Reachy Mini Personal Assistant", "Face tracking, cron job orchestration, notifications")
        System(reachy, "Reachy Mini Robot", "Camera, speakers, motor control")
        System(storage, "SQLite Database", "Calendar events & application data")
      }

      Person(user, "End User", "Interacts via gestures and proximity")

      System_Boundary(notification_services, "Notification Services") {
        System_Ext(slack, "Slack", "Notification delivery")
        System_Ext(telegram, "Telegram", "Notification delivery")
      }

      System_Boundary(data_sources, "External Data Sources") {
        System_Ext(gatech, "GaTech Calendar", "Academic calendar events")
        System_Ext(createx, "Create-X Calendar", "Maker space events")
        System_Ext(hive, "Hive Calendar", "Community events")
        System_Ext(arxiv, "arXiv API", "Research papers (security & crypto)")
      }

      Rel(gatech, assistant, "Provides calendar events (daily)")
      Rel(createx, assistant, "Provides calendar events (weekly)")
      Rel(hive, assistant, "Provides calendar events (weekly)")
      Rel(arxiv, assistant, "Provides research papers (daily)")

      Rel(assistant, storage, "Reads/writes calendar events & data")
      Rel(assistant, reachy, "Controls motors, reads camera, plays audio")
      Rel(user, reachy, "Interacts via gestures and proximity")

      Rel(assistant, slack, "Sends notifications (if configured)")
      Rel(assistant, telegram, "Sends notifications (if configured)")
```

## Reachy Mini Overview

The Reachy Mini is a small humanoid robot developed by the French company Pollen Robotics. It is designed for research, education, and personal use. The robot features a modular design, allowing users to customize its appearance and functionality. It has a range of sensors, including cameras, and microphones, enabling it to interact with its environment and users effectively.

The Reachy Mini uses a client-server architecture, where the robot runs a server that can be controlled through a client interface. This allows for flexibility in programming and integration with various services and applications:
