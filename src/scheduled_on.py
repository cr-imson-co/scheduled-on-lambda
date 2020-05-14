#!/usr/bin/env python
'''
#
# cr.imson.co
#
# Automated hourly startup service for EC2 instances
#
# @author Damian Bushong <katana@odios.us>
#
'''

# pylint: disable=C0116,C0301,C0411,W0511,W1202

from datetime import datetime
import time

from crimsoncore import LambdaCore

from aws_xray_sdk.core import patch_all
patch_all()

LAMBDA_NAME = 'scheduled_on'
LAMBDA = LambdaCore(LAMBDA_NAME)
LAMBDA.init_ec2()
LAMBDA.init_s3()
LAMBDA.init_sns()

class RecoveredError(Exception): # pylint: disable=C0115
    pass

def lambda_handler(event, context):
    start_time = str(int(time.time() * 1000))
    log_name = f'{LAMBDA_NAME}_{start_time}.log'
    LAMBDA.change_logfile(log_name)

    try:
        # pylint apparently doesn't understand that LAMBDA.ec2 is lazy-loaded.  disabling the rule for that line.
        current_hour = datetime.utcnow().strftime('%H')
        instances = list(LAMBDA.ec2.instances.filter(Filters=[ # pylint: disable=E1101
            {
                'Name': 'tag:scheduled_on',
                'Values': [current_hour]
            },
            {
                'Name': 'instance-state-name',
                'Values': ['stopped']
            }
        ]))

        if len(instances) > 0:
            had_failures = False
            for instance in instances:
                LAMBDA.logger.info(f'Starting instance {instance.id}')

                try:
                    instance.start()
                except Exception: # pylint: disable=W0703
                    LAMBDA.logger.error(f'Failed to start instance {instance.id}', exc_info=True)
                    had_failures = True

            if had_failures:
                raise RecoveredError('One or more instance control failures occurred')
        else:
            LAMBDA.logger.info('No instances to start.')
    except Exception:
        LAMBDA.logger.error('Fatal error during script runtime', exc_info=True)

        # do our best to fire off the emergency flare
        error_log_dest = f'logs/{LAMBDA_NAME}/{log_name}'
        with open(f'{LAMBDA.config.get_log_path()}/{log_name}', 'r') as file:
            LAMBDA.archive_log_file(error_log_dest, file.read())

        # todo: make the error notification appropriate depending on if it's stdout, local, or s3 logging...
        LAMBDA.send_notification('error', f'λ! - {LAMBDA_NAME} lambda error notification - error logs are available at {error_log_dest}')

        raise
    finally:
        LAMBDA.change_logfile(f'{LAMBDA_NAME}_interim.log')
