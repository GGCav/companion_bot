# Companion Bot
The goal of this project is to create a pet-companion robot that utilizes LLM-based artificial intelligence to continually produce character, while empowering emotional interaction via voice, touch, and visual channels. A Raspberry Pi 4 is the core controller running a personality engine that monitors several discrete emotional states (e.g., happy, curious, lonely, excited, sleepy) that adapt behaviors in reaction to user input and environmental context. Input modes include (1) a microphone to enable voice activation, (2) distributed touch sensors as input to detect petting, (3) a Pi Camera for facial recognition and object tracking, and (4) proximity sensors for spatial awareness. The robot has a TFT display that provides over 20 different animated eye expressions to reflect the internal state and servo motors for lifelike head, ear, and tail movements. The LLM functionality is provided through cloud APIs or on device models (Ollama). We also have a memory module that integrates user preferences, interaction history, and learned routines into our reasoning process to support long-term relationship modeling. The personality engine combines multimodal input, applies state-machine or dictionary-type logic to govern its output, visual, audio, and physical expressions, as integrated in a concurrent and coherent fashion. 

```flow chart
flowchart TD
    User[User Interaction<br/>Voice, Touch, Vision]
    Mic[Microphone Array]
    Touch[Touch Sensors<br/>Head, Body, Back]
    Camera[Pi Camera<br/>Face Detection]
    STT[Speech-to-Text]
    AICore[LLM Core<br/>GPT API or Local Ollama]
    Personality[Personality Engine<br/>Emotion State Machine]
    Memory[Memory System<br/>User Preferences & History]
    TTS[Text-to-Speech<br/>Pet Voice]
    Emotion[Emotion Display System]
    TFT[TFT Display<br/>Animated Eyes & Expressions]
    Motor[Servo Motors<br/>Head, Tail, Ears]
    Speaker[Speaker Audio Output]
    RobotBody[Lab 3 Robot Kit<br/>Body Movement]
    Sensors[Environmental Sensors<br/>PIR, Proximity]
    
    User --> Mic
    User --> Touch
    User --> Camera
    
    Mic --> STT
    Touch --> Personality
    Camera --> Personality
    Sensors -.-> Personality
    
    STT --> AICore
    AICore --> Memory
    Memory --> Personality
    Personality --> AICore
    
    Personality --> Emotion
    Personality --> TTS
    
    Emotion --> TFT
    Emotion --> Motor
    TTS --> Speaker
    Motor --> RobotBody
    
    subgraph RPI["Raspberry Pi 4 - Central Controller"]
        STT
        AICore
        Personality
        Memory
        TTS
        Emotion
    end
    
    subgraph Output["Multimodal Pet Responses"]
        TFT
        Motor
        Speaker
        RobotBody
    end
    
    style RPI fill:#e1f5dd,stroke:#4caf50,stroke-width:3px
    style Output fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style User fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style Personality fill:#fce4ec,stroke:#e91e63,stroke-width:2px
```
! [Flow Chart](flow_chart.jpg)
