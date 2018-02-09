#!/usr/bin/env python3

import boto3
import time
import subprocess
import sys
import os
import json

ec2 = boto3.resource("ec2")
s3 = boto3.resource("s3")


# create an instance
def create_instance():

    tag_name = input("Please enter tag name of the instance: ")
    key_name = input("Please enter key name: ")
    key_path = input("Please enter path to key: ")

    instance = ec2.create_instances(
        ImageId='ami-acd005d5',
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=['sg-e8c22993'],
        KeyName=key_name,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': tag_name}]}],
        UserData='''#!bin/bash
            yum -y update
            yum -y install python35
            yum -y install nginx
            service nginx start
            chkconfig nginx on
            touch /home/ec2-user/testfile''',
        InstanceType='t2.micro')

    print()
    print("CREATING INSTANCE")
    print("-------------------")
    time.sleep(1)
    print("An instance with ID: ", instance[0].id, " has been created.")
    print()
    print("RETRIEVING PUBLIC IP ADDRESS")
    print("-------------------")
    time.sleep(5)
    instance = instance[0]
    instance.reload()
    print("Public IP address: ", instance.public_ip_address)
    print()
    # create a public ip variable for instance
    pub_ip_inst = instance.public_ip_address

    ssh_check(instance, key_path)
    securecopy_check_webserver(pub_ip_inst, key_path)

    return instance, pub_ip_inst, key_path


# check to see if ssh will work on instance
def ssh_check(instance, key_path):

    # create a public ip variable for instance
    pub_ip_inst = instance.public_ip_address

    # ssh check command
    print("CHECKING SSH ACCESS ON INSTANCE...")
    cmd_ssh_check = "ssh -o StrictHostKeyChecking=no -i " + key_path + " ec2-user@" + pub_ip_inst + " 'pwd'"
    time.sleep(40)
    print("-------------------")
    instance.reload()
    (status, output) = subprocess.getstatusoutput(cmd_ssh_check)
    print("output: " + output)
    print("status: ", status)
    if status == 0:
        print("ssh test passed")
    else:
        print("ssh test failed")

    return pub_ip_inst


# copy check_webserver.py to the instance
def securecopy_check_webserver(pub_ip_inst, key_path):
    time.sleep(2)
    print()
    print("COPYING CHECK_WEBSERVER.PY TO INSTANCE")
    print("-------------------")
    time.sleep(1)
    cmd_scp = "scp -i " + key_path + " check_webserver.py ec2-user@" + pub_ip_inst + ":."
    # carrying out secure copy command
    (status, output) = subprocess.getstatusoutput(cmd_scp)
    print("output: " + output)
    print("status: ", status)
    # check if check_webserver was copied
    if status == 0:
        print("check_webserver successfully copied")
    else:
        print("check_webserver not copied")


# execute the check_webserver
def execute_check_webserver(instance, pub_ip_inst, key_path):
    time.sleep(2)
    print()
    print("MAKING CHECK_WEBSERVER.PY EXECUTABLE")
    print("-------------------")
    time.sleep(1)
    # make the check_webserver.py file executable before its run
    make_executable = "ssh -i " + key_path + " ec2-user@" + pub_ip_inst + " 'chmod +x check_webserver.py'"
    instance.reload()
    (status, output) = subprocess.getstatusoutput(make_executable)
    print("output: " + output)
    print("status: ", status)
    # let user know if check_webserver is executable or not
    if status == 0:
        print("check_webserver is executable")
        time.sleep(2)

        print()
        print("EXECUTING CHECK_WEBSERVER.PY")
        print("-------------------")
        install_python = "ssh -o StrictHostKeyChecking=no -i " + key_path + " ec2-user@" + pub_ip_inst + \
                         " 'sudo yum install -y python35'"
        (status, output) = subprocess.getstatusoutput(install_python)
        time.sleep(1)
        # after informing user that it's executable, run the file
        exe_check_webserver = "ssh -i " + key_path + " ec2-user@" + pub_ip_inst + " './check_webserver.py'"
        print("command to run: ", exe_check_webserver)
        instance.reload()
        (status, output) = subprocess.getstatusoutput(exe_check_webserver)
        # print the output and status of the check_webserver file when run
        print("output: " + output)
        print("status: ", status)
        # let user know whether the file execution was successful or not
        if status == 0:
            print("execute_check_webserver successful")
        else:
            print("execute_check_webserver failed")
            (status, output) = subprocess.getstatusoutput(install_python)
            execute_check_webserver(instance, pub_ip_inst, key_path)
    else:
        print("check_webserver is not executable")


# creating a new bucket
def create_bucket():
    time.sleep(2)
    print()
    print("CREATING A BUCKET")
    print("-------------------")
    time.sleep(1)
    s3 = boto3.client('s3')
    # get bucket name input from user
    bucket_name = input("Please Enter Bucket name (unique): ")
    try:
        # create bucket with location in Ireland
        response = s3.create_bucket(Bucket=bucket_name, ACL='public-read', CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'})

      #  bucket_policy = {
       #     'version': '2012-10-17',
        #    'Statement': [{
         #       'Sid': 'AllowPublicRead',
          #      'Effect': 'Allow',
           #     'Principal': '*',
            #    'Action': ['s3@GetObject'],
             #   'Resource': ['arn:aws:s3:::' + bucket_name + '/*']
           # }]
      #  }

      #  bucket_policy = json.dumps(bucket_policy)
      #  s3.put_bucket_policy(
      #      Bucket=bucket_name,
      #      Policy=bucket_policy
      #  )

        # if bucket successfully created then print message for user
        print("creating bucket successful")
        print(response)
    # if there is an error creating a bucket, print message for user
    except Exception as error:
        print(error)

    return bucket_name


# adding a file to a bucket
def add_file_to_bucket(bucket_name):
    time.sleep(2)
    print()
    print("ADD AN IMAGE TO BUCKET")
    print("-------------------")
    time.sleep(1)
    try:
        object_name = input("name of image: ")
        # command to add the file to the bucket                         # give file readable permission
        response = s3.Object(bucket_name, object_name).put(ACL='public-read', Body=open(object_name, 'rb'))
        print("File added to bucket called: ", bucket_name)
        print("Response: ", response)
    except Exception as error:
        print(error)

    return object_name


def add_file_to_index(instance, pub_ip_inst, bucket_name, object_name):
    time.sleep(2)
    print()
    print("ADD IMAGE TO NGINX HOME PAGE")
    print("-------------------")
    time.sleep(1)
    try:
        # Ask user if they want to add the uploaded file to the index page for this instance
        add_to_index = input("Add this file to nginx home page (Y/N) ?: ")
        if add_to_index.upper() == 'Y':
            # Create a url for the uploaded file
            print("Creating URL for file")
            image_url = "https://s3-eu-west-1.amazonaws.com/" + bucket_name + "/" + object_name
            print(image_url)

            chmod_cmd = "ssh -o StrictHostKeyChecking=no -i ~/dev-ops/paddykeypair.pem ec2-user@" + pub_ip_inst + "sudo chmod +x /usr/share/nginx/html/index.html"
            (output, status) = subprocess.getstatusoutput(chmod_cmd)

            try:
                # command to run to add the image to index.html using the url
                cmd_add_image_to_index = "ssh -o StrictHostKeyChecking=no -i ~/dev-ops/paddykeypair.pem ec2-user@" + pub_ip_inst + " 'echo \"<html>" \
                                        "<img src=" + image_url + " alt=\'Python Image\'/></html>\" " \
                                         "| sudo tee -a /usr/share/nginx/html/index.html'"
                print("command to run: ", cmd_add_image_to_index)
                # run the command and check the output & status
                (status, output) = subprocess.getstatusoutput(cmd_add_image_to_index)
                instance.reload()
                print("output: " + output)
                print("status: ", status)
                # if status is 0 then image was added, else it wasn't
                if status == 0:
                    print("Image has been added to index.html")
                else:
                    print("Error adding image to index.html")

            except Exception as error:
                print(error)
        elif add_file_to_index.upper == 'N':
            print("File not uploaded.")
        else:
            print("Incorrect option entered: ", add_to_index)
    except Exception as error:
        print(error)


def menu():

    print('''
    Welcome to RunNewWebserver
    --------------------------
    1) Create instance & bucket & add image 
    2) Create instance 
    3) Create bucket 
    4) Add image to bucket
    5) Add image to nginx
    6) Run check_webserver
    0. Exit\n
    ''')


def main():

    while True:
        menu()
        menu_option = input("Please Enter Command: ")
        print()
        if menu_option == "1":
            instance, pub_ip_inst, key_path = create_instance()
            execute_check_webserver(instance, pub_ip_inst, key_path)
            bucket_name = create_bucket()
            object_name = add_file_to_bucket(bucket_name)
            add_file_to_index(instance, pub_ip_inst, bucket_name, object_name)


if __name__ == '__main__':
    main()
