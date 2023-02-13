# Required: Python 3.11 or later. Modules see below.
# No VPN connection needed (login via apiToken)
import asyncio
import os
from websockets import client as ws
import sys
import time
import avh_api_async as AvhAPI # AVH async API module, see https://github.com/arm-software/avh-api

import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

## REST API ACCESS
apiEndpoint = 'https://arm.corellium.io/api' # for avh.arm.com change to https://app.avh.arm.com/api
# For arm.correlium.io fixed token is used (shared separately). On avh.arm.com it is unique per account
apiToken = ''


## INSTANCE SETUP SETTINGS
modelName = 'efr32mg24' # Model type when creating a new instance
instanceName = 'test_efr32' # Instance name when creating a new one
instanceId = None # set to instance ID if an already existing instance shall be used (format: '415f9ac2-dd9f-438a-bcf8-84d57090f6f5')
deleteNewInstance = True # set to True to delete the created VM instance after execution. If existing instance is used, it will be not deleted

## FIRMWARE
fwFile = os.path.join(sys.path[0], 'i2cspm_kernel_freertos.axf') # provide path to the local firmware file

## EXECUTION CONFIG
t_run = 5 # time duration for running the firmware in seconds

## LOCAL VARIABLES
version = 0
exitStatus = 0

# wait until instance has required state
async def waitForState(api_instance, instance, state):
  instanceState = await api_instance.v1_get_instance_state(instance.id)
  while (instanceState != state):
    if (instanceState == 'error'):
      raise Exception('VM entered error state')
    await asyncio.sleep(0.1)
    instanceState = await api_instance.v1_get_instance_state(instance.id)

# create new instance of modelName type and with given vmName
async def createInstance(api_instance, modelName, vmName):
  print('Finding a project...')
  api_response = await api_instance.v1_get_projects()
  projectId = api_response[0].id
  print('Chosen project ID: {}\n'.format(projectId))

  print('Finding target model {}...'.format(modelName))
  api_response = await api_instance.v1_get_models()
  chosenModel = None
  for model in api_response:
    if model.flavor.startswith(modelName):
      chosenModel = model
      break

  print("done.\n")

  api_response = await api_instance.v1_get_model_software(model.model)
  chosenSoftware = None
  for software in api_response:
    if software.filename.startswith(modelName): # just taking first available SW to start with. Will be overwritten later.
      chosenSoftware = software
      break

  print('Chosen software to start: {}\n'.format(chosenSoftware.filename))

  print('Creating a new instance...')
  api_response = await api_instance.v1_create_instance({
    "name": vmName,
    "project": projectId,
    "flavor": chosenModel.flavor,
    "os": chosenSoftware.version,
    "osbuild": chosenSoftware.buildid
  })
  instance = api_response
  print('done. Instance ID: {}'.format(instance.id))
  print('Waiting for the instance to start...')
  await waitForState(api_instance, instance, 'on')

  return instance


async def main():
  error = None
  console = None
  deleteInstance = deleteNewInstance

  configuration = AvhAPI.Configuration(
      host = apiEndpoint
  )

  async with AvhAPI.ApiClient(configuration=configuration) as api_client:
    api_instance = AvhAPI.ArmApi(api_client)
    instance = None

    token_response = await api_instance.v1_auth_login({
      "apiToken": apiToken,
    })

    print('Logged in\n')
    configuration.access_token = token_response.token

    try:
      print('Obtaining target VM instance...')
      if instanceId:
        print('Existing instance to be used: {}'.format(instanceId))
        api_response = await api_instance.v1_get_instance(instanceId)
        instance = api_response
        deleteInstance = False # if using an existing instance, do not delete it
      else:
        print('New instance to be created.')
        api_response = await createInstance(api_instance, modelName, instanceName)
        instance = api_response
      print('done\n')
            
      print('Getting instance console...')
      consoleEndpoint = await api_instance.v1_get_instance_console(instance.id)
      console = await ws.connect(consoleEndpoint.url, ssl=ctx)
      print('done\n')


      print('Loading the FW image: {}'.format(fwFile))
      fwImage = await api_instance.v1_create_image('fwbinary', 'plain',
       name = os.path.basename(fwFile),
       instance = instance.id,
       file = fwFile
      )
      print('done\n')

      print('Resetting the instance to use the new firmware')
      console.messages.clear()
      api_response = await api_instance.v1_reboot_instance(instance.id)
      await waitForState(api_instance, instance, 'on')
      print('done\n')

      t1 = time.perf_counter()
      print('Running the program for {} seconds'.format(t_run))
      
      # Getting current temperature
      api_response = await api_instance.v1_get_instance_peripherals(instance.id)
      curr_temp = api_response.temperature
      print('Current temperature {} '.format(curr_temp))

      # Getting current LED status
      api_response = await api_instance.v1_get_instance_gpios(instance.id)
      print('LED status: {}'.format(api_response.led.banks))
      
      print('Running with current settings...')
      time.sleep(2) # run 2 sec with current settings

      # Increasing temperature 
      print('Increasing temperature by 10 degrees')
      peripherals_data = {
       "temperature": curr_temp+10,
      } 
      api_response = await api_instance.v1_set_instance_peripherals(instance.id,peripherals_data)
      
      # Getting current temperature
      api_response = await api_instance.v1_get_instance_peripherals(instance.id)
      print('Current temperature {}'.format(api_response.temperature))

      time.sleep(0.5) # await a bit to accomodate the reading delays in fw
      
      # Getting current LED status
      api_response = await api_instance.v1_get_instance_gpios(instance.id)
      print('LED status: {}'.format(api_response.led.banks))
      
      # Getting console output
      text = ''
      async for message in console:
        t2 = time.perf_counter()
        text += message.decode('utf-8')
        if (t2-t1) >= t_run:
          break
      
      print('\n=== UART output log: ====')
      print(text)
      print('=== End of UART output log: ====\n')

    except asyncio.TimeoutError as e:
      print('Run failed: timeout')
      error = e
    except Exception as e:
      print('Encountered error; cleaning up...')
      error = e
    finally:
      if console:
        print('Closing console connection...')
        console.close_timeout = 1
        api_response = await console.close()
        print('done.\n')
      if instance and deleteInstance:
        print('Deleting the virtual instance...')
        api_response = await api_instance.v1_delete_instance(instance.id)
        print('done.\n')
      if error != None:
        raise error

# Run with timeout of 60 seconds
asyncio.run(asyncio.wait_for(main(),60)) 

print("Execution completed!")
exit(0)