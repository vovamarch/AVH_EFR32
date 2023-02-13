# AVH_EFR32
Arm Virtual Hardware example for EFR32

## Overview
The `avh_run_efr32mg24.py` demonstrates key steps in using [AVH python API](https://github.com/arm-software/avh-api) for automated program executions. The execution flow is as follows:
 - Connect to the AVH API.
 - Create a new virtual machine instance of EFR32MG24 board (or reconfigure to use existing instance).
 - Load firmware binary `i2cspm_kernel_freertos.axf` (I2C SPM FreeRTOS Application build in Simplicity Studio) to the VM instance and reboots it.
 - Read temperature and LEDs status.
 - Increase the temperature by 10 degrees that shall lead to LED toggle.
 - Read the temperature and LEDs status.
 - Print the UART output.
 - Delete the instance (or if configured keep it for future use).
 
Verified with python 3.11.

## Use instructions

1) Clone the repo

2) Install python requirements run: ```pip install -r requirements.txt```

3) In `avh_run_efr32mg24.py`  provide value for  `apiToken` that is shared separately.

4) Run in command line: ```python avh_run_efr32mg24.py```

5) Example execution output:
```
>python avh_run_efr32mg24.py
Logged in

Obtaining target VM instance...
New instance to be created.
Finding a project...
Chosen project ID: a12063e0-636b-4008-99d0-09f9499e3b6f

Finding target model efr32mg24...
done.

Chosen software to start: efr32mg24_humditysensor_demo.coreimg-d4eb0de4-755f-44cf-a222-66f3289f21a2

Creating a new instance...
done. Instance ID: b0f5a5cc-8427-4871-8ecb-f9d5ae059ef7
Waiting for the instance to start...
done

Getting instance console...
done

Loading the FW image: c:\Users\vlamar01\SimplicityStudio\v5_workspace\binaries\i2cspm_kernel_freertos.axf
done

Resetting the instance to use the new firmware
done

Running the program for 5 seconds
Current temperature 25.0
LED status: [[0, 0, 1]]
Running with current settings...
Increasing temperature by 10 degrees
Current temperature 35.0
LED status: [[1, 0, 1]]

=== UART output log: ====

Welcome to the I2C SPM sample application using FreeRTOS


Relative Humidity = 54%
Temperature = 25 C

Relative Humidity = 54%
Temperature = 25 C

Relative Humidity = 54%
Temperature = 25 C

Relative Humidity = 54%
Temperature = 35 C
Turning LED0 on!

Relative Humidity = 54%
Temperature = 35 C
Turning LED0 on!

Relative Humidity = 54%
Temperature = 35 C
Turning LED0 on!

R
=== End of UART output log: ====

Closing console connection...
done.

Deleting the virtual instance...
done.

Execution completed!
>
```

6) If script is stuck or failed and instance is not deleted, delete it via web UI.