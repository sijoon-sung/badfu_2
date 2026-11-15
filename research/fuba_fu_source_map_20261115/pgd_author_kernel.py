"""IBM notebook interpretation, explicitly using squared distances and a > stop."""
import numpy as np
import torch
from torch import nn


def squared_distance(model,reference):
    with torch.no_grad():
        a=nn.utils.parameters_to_vector(model.parameters())
        b=nn.utils.parameters_to_vector(reference.parameters())
        if not bool(torch.isfinite(a).all() & torch.isfinite(b).all()):raise ValueError('Nonfinite parameter')
        return torch.square(torch.norm(a-b))


def radius_squared(reference,random_models):
    if len(random_models)!=10:raise ValueError('The source radius uses exactly10 random models')
    # np.mean follows the exact source dtype/reduction policy.
    return np.mean([squared_distance(reference,m) for m in random_models])/3


def project_author_(model,reference,*,radius_squared):
    if not np.isfinite(radius_squared) or radius_squared<0:raise ValueError('Invalid squared radius')
    with torch.no_grad():
        if squared_distance(model,reference)>radius_squared:
            v=nn.utils.parameters_to_vector(model.parameters())-nn.utils.parameters_to_vector(reference.parameters())
            v=v/torch.norm(v)*np.sqrt(radius_squared)
            projected=nn.utils.parameters_to_vector(reference.parameters())+v
            nn.utils.vector_to_parameters(projected,model.parameters())
    return model


def stop_author(model,deleted_client,*,distance_threshold):
    if not np.isfinite(distance_threshold) or distance_threshold<0:raise ValueError('Invalid squared threshold')
    return bool(squared_distance(model,deleted_client)>distance_threshold)
