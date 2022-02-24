import os

from azureml.core import Workspace, Dataset, Datastore, Model
from azureml.core import Environment, Experiment, ScriptRunConfig

from azureml.core.authentication import ServicePrincipalAuthentication

from azureml.core.compute import AmlCompute, ComputeTarget, ComputeInstance
from azureml.core.compute_target import ComputeTargetException

from azureml.core.webservice import AciWebservice
from azureml.core.model import InferenceConfig

import dotenv
dotenv.load_dotenv()


WS_NAME = os.environ.get('WS_NAME')
SUBSCRIPTION = os.environ.get('SUBSCRIPTION_ID_SPONSORSHIP')
RESSOURCE_GROUP = os.environ.get('RESSOURCE_GROUP')



def upload_and_register_datasets(
                    ds_path, 
                    datasets_folder='././00_data/datasets',
                    datastore='default'):

    ws = get_ws()

    if datastore =='default':
        datastore = ws.get_default_datastore()
            
    datastore.upload(src_dir=datasets_folder,
                    target_path=ds_path,
                    overwrite=True)

    datastore_paths = [(datastore, ds_path)]
    dataset = Dataset.File.from_files(path=datastore_paths)

    dataset.register(
        workspace=ws,
        name="utterances",
        description="Train and test utterances for LUIS App 1",
        create_new_version=True
    )

    return None

def get_dataset(name):
    ws = get_ws()
    ds = ws.datasets[name]
    # ds = Dataset.get_by_name(ws, name)
    return ds


def get_compute(compute_name='p10-cpu', instance_or_cluster='instance'):
    ws = get_ws()

    try:
        if instance_or_cluster == "instance":
            compute_target = ComputeTarget(workspace=ws, name=compute_name)
            print('Found existing instance, use it.')
        else:
            compute_target = ComputeInstance(workspace=ws, name=compute_name)  
            print('Found existing cluster, use it.')
    except:
        # defining a instance configuration..
        if instance_or_cluster == "instance":
            compute_config = ComputeInstance.provisioning_configuration(
                vm_size='Standard_D11_v2',
                )
            # create instance
            compute_target = ComputeInstance.create(ws, compute_name, compute_config)
            compute_target.wait_for_completion(show_output=True)
        else:
            # defining a cluster configuration..
            compute_config = AmlCompute.provisioning_configuration(
                location = 'northeurope',
                vm_size='Standard_D11',
                min_nodes=0,
                max_nodes=3
                )
            # create the cluster (for distributed runs)
            compute_target = ComputeTarget.create(ws,compute_name,compute_config)   
            compute_target.wait_for_completion(show_output=True)
    
    return compute_target


def get_env(dir, file, env_name='p10_env', create=False):
    # On spécifie les packages à installer from dir/env.yml
    
    ws=get_ws()

    if create == False:
        env = Environment.get(workspace=ws, name=env_name)
    else:
        env = Environment.from_conda_specification(
            name=env_name,
            file_path=os.path.join(dir, file)
        )
        # On enregistre l'environnement
        env.register(workspace=ws)

    return env

def get_ws(credentials=None):

    try:
        WS_NAME = os.environ.get('WS_NAME')
        SUBSCRIPTION_ID_SPONSORSHIP = os.environ.get('SUBSCRIPTION_ID_SPONSORSHIP')
        RESSOURCE_GROUP = os.environ.get('RESSOURCE_GROUP')

        TENANT_ID = os.environ.get('TENANT_ID')
        APP_ID = os.environ.get('APP_ID')
        APP_PASSWORD = os.environ.get('APP_PASSWORD')
    except:
        WS_NAME = credentials.get('WS_NAME')
        SUBSCRIPTION_ID_SPONSORSHIP = credentials.get('SUBSCRIPTION_ID_SPONSORSHIP')
        RESSOURCE_GROUP = credentials.get('RESSOURCE_GROUP')

        TENANT_ID = credentials.get('TENANT_ID')
        APP_ID = credentials.get('APP_ID')
        APP_PASSWORD = credentials.get('APP_PASSWORD')


    svc_pr = ServicePrincipalAuthentication(
        tenant_id=TENANT_ID,
        service_principal_id=APP_ID,
        service_principal_password=APP_PASSWORD)

    # # si WS n'existe pas, il faut le créer
    # try:
    #     ws = Workspace.get(name=WS_NAME,
    #             subscription_id=SUBSCRIPTION,
    #             resource_group=RESSOURCE_GROUP)
    # except:
    #     ws = Workspace.create(name=WS_NAME,
    #                         subscription_id=SUBSCRIPTION,
    #                         resource_group=RESSOURCE_GROUP,
    #                         create_resource_group=False,
    #                         location='northeurope'
    #                         )
    ws = Workspace(
        subscription_id=SUBSCRIPTION_ID_SPONSORSHIP,
        resource_group=RESSOURCE_GROUP,
        workspace_name=WS_NAME,
        auth=svc_pr
        )
    return ws
