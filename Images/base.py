from flask import Blueprint, request
import json
import os
import shutil
import yaml
import docker
import zipfile
from kubernetes import client, config

option = Blueprint('images', __name__)


# set docker and k8s client
docker_client = docker.from_env()
config.load_kube_config()

#######################
# image options
#######################


@option.route("/image/list", methods=['GET'])
def list_images():
    images = docker_client.images.list()
    arr = []
    for image in images:
        dic = dict()
        dic["attrs"] = image.attrs
        dic["id"] = image.id
        dic["labels"] = image.labels
        dic["short_id"] = image.short_id
        dic["tags"] = image.tags
        arr.append(dic)
    return {"data": arr}


@option.route("/image/pull", methods=['POST'])
def pull_image():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        docker_client.images.pull(repository=json_data.get("repository"))
        ret = {"msg": "pull success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/image/remove", methods=['POST'])
def remove_image():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        docker_client.images.remove(json_data.get("image_id"))
        ret = {"msg": "delete success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/image/build", methods=['POST'])
def build_image():
    try:
        tmp_path = "tmp_build_space"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)
        file = request.files.get('dockerfile')
        file.save(os.path.join(tmp_path, file.filename))
        zip_file_path = os.path.join(tmp_path, file.filename)
        unzip_directory = os.path.join(tmp_path)
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(unzip_directory)
        contents = os.listdir(unzip_directory)
        folder_name = None
        for item in contents:
            item_path = os.path.join(unzip_directory, item)
            if os.path.isdir(item_path):
                folder_name = item
                break
        target_dir = os.path.join(unzip_directory, folder_name)
        print(target_dir)
        build_result, build_logs = docker_client.images.build(
            path=target_dir, tag=request.form['tag'], rm=True
        )
        shutil.rmtree(tmp_path)
        ret = {"msg": "build success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


#######################
# container options
#######################


@option.route("/container/list", methods=['GET'])
def list_containers():
    containers = docker_client.containers.list(all=True)
    arr = []
    for container in containers:
        dic = dict()
        dic["id"] = container.id
        dic['name'] = container.name
        dic['image'] = {'id': container.image.id, 'tags': container.image.tags}
        dic["labels"] = container.labels
        dic["short_id"] = container.short_id
        dic["status"] = container.status
        arr.append(dic)
    return {"data": arr}


@option.route("/container/run", methods=['POST'])
def run_container():
    try:
        command = request.values.getlist('command_box')
        environment = request.values.getlist('environment_box')
        container_ports = request.values.getlist('container_ports_box')
        host_posts = request.values.getlist('host_posts_box')
        volumes = request.values.getlist('volumes_box')
        ports = {}
        for cp, hp in zip(container_ports, host_posts):
            ports[cp] = hp
        docker_client.containers.run(image=request.form['image'], name=request.form['name'], command=command,
                                     environment=environment, ports=ports, volumes=volumes, detach=True)
        return {"msg": "create success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/rename", methods=['POST'])
def rename_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))
        container.rename(json_data.get('new_name'))
        return {"msg": "rename success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/restart", methods=['POST'])
def restart_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))
        container.restart()
        return {"msg": "restart success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/start", methods=['POST'])
def start_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))
        container.start()
        return {"msg": "start success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/stop", methods=['POST'])
def stop_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))
        container.stop()
        return {"msg": "stop success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/remove", methods=['POST'])
def remove_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))
        container.remove()
        return {"msg": "remove success"}
    except Exception as err:
        return {"msg": str(err)}


@option.route("/container/commit", methods=['POST'])
def commit_container():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        container = docker_client.containers.get(json_data.get('container_id'))

        changes = None
        if 'changes' in json_data:
            changes = json_data.get('changes')

        container.commit(repository=json_data.get('repository'), tag=json_data.get('tag'),
                         message=json_data.get('message'),
                         author=json_data.get('author'), changes=changes)
        return {"msg": "commit success"}
    except Exception as err:
        return {"msg": str(err)}


#######################
# kubernetes
#######################


@option.route("/list_nodes", methods=['GET'])
def list_nodes():
    ret = client.CoreV1Api().list_node()
    arr = []
    for i in ret.items:
        dic = dict()
        dic['kind'] = i.kind
        dic['name'] = i.metadata.name
        dic['namespace'] = i.metadata.namespace
        dic['creation_timestamp'] = i.metadata.creation_timestamp
        dic['allocatable'] = i.status.allocatable
        dic['phase'] = i.status.phase
        arr.append(dic)
    return {"data": arr}


@option.route("/list_pods", methods=['GET'])
def list_pods():
    ret = client.CoreV1Api().list_pod_for_all_namespaces(watch=False)
    arr = []
    for i in ret.items:
        dic = dict()
        dic['namespace'] = i.metadata.namespace
        dic['name'] = i.metadata.name
        dic['creation_timestamp'] = i.metadata.creation_timestamp
        dic['pod_ip'] = i.status.pod_ip
        container_statuses = []
        for status in i.status.container_statuses:
            s = dict()
            s['name'] = status.name
            s['container_id'] = status.container_id
            s['image_id'] = status.image_id
            s['image'] = status.image
            s['ready'] = status.ready
            container_statuses.append(s)
        dic['container_statuses'] = container_statuses
        dic['node_name'] = i.spec.node_name
        arr.append(dic)
    return {"data": arr}

# deployment


@option.route("/deployment/list", methods=['GET'])
def list_deployments():
    ret = client.AppsV1Api().list_deployment_for_all_namespaces()
    arr = []
    for i in ret.items:
        dic = dict()
        dic['name'] = i.metadata.name
        dic['creation_timestamp'] = i.metadata.creation_timestamp
        dic['namespace'] = i.metadata.namespace
        dic['available_replicas'] = i.status.available_replicas
        dic['replicas'] = i.status.replicas
        arr.append(dic)
    return {"data": arr}


@option.route("/deployment/delete", methods=['POST'])
def delete_deployment():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        client.AppsV1Api().delete_namespaced_deployment(
            name=json_data.get('name'), namespace=json_data.get('namespace')
        )
        ret = {"msg": "delete success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/deployment/yml/create", methods=['POST'])
def create_deployment_yml():
    try:
        dep = yaml.safe_load(request.files.get('config'))
        client.AppsV1Api().create_namespaced_deployment(body=dep, namespace=request.form['namespace'])
        ret = {"msg": "create success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/deployment/param/create", methods=['POST'])
def create_deployment_param():
    try:
        deployment_name = request.form['name']
        deployment_image = request.form['image']
        environment_names = request.values.getlist('environment_names')
        environment_values = request.values.getlist('environment_values')
        container_ports = request.values.getlist('container_ports')
        ports = list()
        envs = list()
        if len(environment_names) != len(environment_values):
            return {"msg": "Not matched in environment settings."}
        for p in container_ports:
            ports.append(
                client.V1ContainerPort(container_port=int(p))
            )
        for i in range(len(environment_names)):
            envs.append(
                client.V1EnvVar(name=environment_names[i], value=environment_values[i])
            )
        
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1DeploymentSpec(
                replicas=int(request.form['replicas']),
                selector=client.V1LabelSelector(
                    match_labels={"app": "my-app"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "my-app"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=deployment_name,
                                image=deployment_image,
                                ports=ports,
                                env=envs
                            )
                        ]
                    )
                )
            )
        )
        client.AppsV1Api().create_namespaced_deployment(body=deployment, namespace=request.form['namespace'])
        ret = {"msg": "create success"}
    except Exception as err:
        ret = {"msg": str(err)}
        import traceback
        traceback.print_exc()
    return ret


@option.route("/deployment/yml/update", methods=['POST'])
def update_deployment_yml():
    try:
        dep = yaml.safe_load(request.files.get('config'))
        client.AppsV1Api().replace_namespaced_deployment(
            body=dep, name=request.form['name'], namespace=request.form['namespace']
        )
        ret = {"msg": "update success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/deployment/param/update", methods=['POST'])
def update_deployment_param():
    try:
        deployment_name = request.form['name']
        deployment_image = request.form['image']
        environment_names = request.values.getlist('environment_names')
        environment_values = request.values.getlist('environment_values')
        container_ports = request.values.getlist('container_ports')
        ports = list()
        envs = list()
        if len(environment_names) != len(environment_values):
            return {"msg": "Not matched in environment settings."}
        for p in container_ports:
            ports.append(
                client.V1ContainerPort(container_port=int(p))
            )
        for i in range(len(environment_names)):
            envs.append(
                client.V1EnvVar(name=environment_names[i], value=environment_values[i])
            )
        
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1DeploymentSpec(
                replicas=int(request.form['replicas']),
                selector=client.V1LabelSelector(
                    match_labels={"app": "my-app"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "my-app"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=deployment_name,
                                image=deployment_image,
                                ports=ports,
                                env=envs
                            )
                        ]
                    )
                )
            )
        )
        client.AppsV1Api().replace_namespaced_deployment(body=deployment, name=request.form['name'], namespace=request.form['namespace'])
        ret = {"msg": "update success"}
    except Exception as err:
        ret = {"msg": str(err)}
        import traceback
        traceback.print_exc()
    return ret

# service


@option.route("/service/list", methods=['GET'])
def list_services():
    ret = client.CoreV1Api().list_service_for_all_namespaces()
    arr = []
    for i in ret.items:
        dic = dict()
        dic['name'] = i.metadata.name
        dic['creation_timestamp'] = i.metadata.creation_timestamp
        dic['namespace'] = i.metadata.namespace
        dic['cluster_ip'] = i.spec.cluster_ip
        dic['external_i_ps'] = i.spec.external_i_ps
        dic['type'] = i.spec.type
        ports = []
        for p in i.spec.ports:
            tem = dict()
            tem['node_port'] = p.node_port
            tem['port'] = p.port
            tem['protocol'] = p.protocol
            ports.append(tem)
        dic['ports'] = ports
        arr.append(dic)
    return {"data": arr}


@option.route("/service/create", methods=['POST'])
def create_service():
    try:
        dep = yaml.safe_load(request.files.get('config'))
        client.CoreV1Api().create_namespaced_service(body=dep, namespace=request.form['namespace'])
        ret = {"msg": "create success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/service/delete", methods=['POST'])
def delete_service():
    try:
        json_data = json.loads(request.get_data().decode('utf-8'))
        client.CoreV1Api().delete_namespaced_service(name=json_data.get('name'), namespace=json_data.get('namespace'))
        ret = {"msg": "delete success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret


@option.route("/service/update", methods=['POST'])
def update_service():
    try:
        dep = yaml.safe_load(request.files.get('config'))
        client.CoreV1Api().replace_namespaced_service(
            body=dep, name=request.form['name'], namespace=request.form['namespace']
        )
        ret = {"msg": "update success"}
    except Exception as err:
        ret = {"msg": str(err)}
    return ret
