# Todo
### Hardware
- [ ] **documentation** make a list of all the hardware components needed for the project
- [ ] **Architecture** all sensors should be easily implementable to microcontroller and, the String output should be automatically updated in the microcontroller when new sensors are added to the system
    - [ ] **implementation** implement all hardware components and test them individually
        - [ ] **implementation** of humidity sensor
            - [ ] implement 1 sensor and test it
            - [ ] make it expandable for more sensors in the future
        - [ ] **implementation** of temperature sensor 
            - [x] implement 1 sensor and test it
            - [ ] make it expandable for more sensors in the future
        - [ ] **implementation** of pressure sensor
            - [ ] implement 1 sensor and test it
            - [ ] make it expandable for more sensors in the future
        - [ ] **implementation** of airflow sensor
            - [ ] implement 1 sensor and test it
            - [ ] make it expandable for more sensors in the future
- [x] **Architecture** the string output of the microcontroller should be able to be read by the server on the computer even when there's new sensors added to the system
    - [x] implement a way to read the string output of the microcontroller on the server
    - [x] make sure that the string output is updated automatically when new sensors are added to the system
- [ ] **Sensor Refactoring** test the Power measture senor more deeople because it can have possible power losses and it can be a problem for the system if this is true
    - [ ] **Hardware Refactoring** if there are power losses, find a way to fix it and make sure that the system is stable and reliable or find a different sensor that can be used for power measurement

### PCB
- [ ] **Design** PCB
    - [ ] **architecture** make a PCB design that can accommodate all the hardware components and make it easy to connect them together
    - [ ] **architecture** make sure that the PCB design has extra connectors for future expansion of the system and additional sensors -> this feeds back to software architecture and hardware architecture because the software should be able to handle new sensors and the hardware should be able to accommodate them and a possible way to configure the sensor connections in software and hardware should be implemented
        - [ ] **todo** define a standard expansion connector type and pinout (power, ground, data lines)
        - [ ] **todo** reserve at least 2 spare expansion headers for future sensors
        - [ ] **todo** document connector electrical limits (voltage, current, max sensor load)
        - [ ] **todo** create a sensor slot map (I2C, SPI, analog, UART) with conflict rules
        - [ ] **todo** add jumper or DIP options for configurable sensor addressing where needed
        - [ ] **todo** add test points for power rails and sensor data lines
        - [ ] **todo** define a software sensor-configuration table format (sensor type, bus, address, label)
        - [ ] **todo** implement backend parsing rules so new sensor fields can be added without breaking telemetry
        - [ ] **todo** add a validation checklist for adding a new sensor (hardware wiring + backend + frontend + CSV schema)
        - [ ] **todo** verify the full expansion flow with one mock future sensor before PCB release
    - [ ] **implementation** implement the PCB design and test it with the hardware components to make sure that everything is working properly and there are no issues with the connections or power supply
### Software
#### ESP32 ./src/
- [ ] **Refactoring** put the part of the code that handels the Serial communication in a separate file and make it a function that can be called in the main loop and more readable
- [ ] **Refactoring** put the part of the code that handels the sensors in a separate file and make it a function that can be called in the main loop and more readable
- [ ] **Refactoring** make the code more modular and easier to read by using functions and classes
#### Server ./tools/web_gui/
- [ ] **feature** 