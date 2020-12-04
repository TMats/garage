#!/usr/bin/env python3
"""This is an example to train MAML-TRPO on ML10 environment."""
# pylint: disable=no-value-for-parameter
# yapf: disable
import click
import torch

from garage import wrap_experiment
from garage.envs import MetaWorldSetTaskEnv
from garage.experiment import (MetaEvaluator, MetaWorldTaskSampler,
                               SetTaskSampler)
from garage.experiment.deterministic import set_seed
from garage.sampler import RaySampler
from garage.torch.algos import MAMLTRPO
from garage.torch.policies import GaussianMLPPolicy
from garage.torch.value_functions import LinearFeatureValueFunction
from garage.trainer import Trainer

# yapf: enable
@click.command()
@click.option('--seed', type=int, default=1)
@click.option('--epochs', type=int, default=2000)
@click.option('--rollouts_per_task', type=int, default=10)
@click.option('--meta_batch_size', type=int, default=20)
@click.option('--inner_lr', default=1e-3, type=float)
@wrap_experiment(snapshot_mode='gap', name_parameters='passed', snapshot_gap=50)
def maml_trpo_metaworld_ml10(ctxt, seed, epochs, rollouts_per_task, meta_batch_size, inner_lr):
    """Set up environment and algorithm and run the task.

    Args:
        ctxt (garage.experiment.ExperimentContext): The experiment
            configuration used by Trainer to create the snapshotter.
        seed (int): Used to seed the random number generator to produce
            determinism.
        epochs (int): Number of training epochs.
        rollouts_per_task (int): Number of rollouts per epoch per task
            for training.
        meta_batch_size (int): Number of tasks sampled per batch.

    """
    set_seed(seed)

    ml10 = metaworld.ML10()
    tasks = MetaWorldTaskSampler(
        ml10,
        'train',
    )
    env = tasks.sample(10)[0]()
    test_sampler = SetTaskSampler(
        MetaWorldSetTaskEnv,
        env=MetaWorldSetTaskEnv(ml10, 'test'),
    )
    num_test_envs = 5

    policy = GaussianMLPPolicy(
        env_spec=env.spec,
        hidden_sizes=(128, 128),
        hidden_nonlinearity=torch.tanh,
        output_nonlinearity=torch.tanh,
        min_std=0.5,
        max_std=1.5,
        std_mlp_type='share_mean_std'
    )

    value_function = LinearFeatureValueFunction(env_spec=env.spec,)

    meta_evaluator = MetaEvaluator(test_task_sampler=test_sampler,
                                   n_exploration_eps=rollouts_per_task,
                                   n_test_tasks=num_test_envs * 2,
                                   n_test_episodes=10)

    sampler = RaySampler(agents=policy,
                         envs=env,
                         max_episode_length=env.spec.max_episode_length,
                         n_workers=meta_batch_size)

    trainer = Trainer(ctxt)
    algo = MAMLTRPO(env=env,
                    policy=policy,
                    sampler=sampler,
                    task_sampler=tasks,
                    value_function=value_function,
                    meta_batch_size=meta_batch_size,
                    discount=0.99,
                    gae_lambda=1.,
                    inner_lr=inner_lr,
                    num_grad_updates=1,
                    meta_evaluator=meta_evaluator,
                    entropy_method='max',
                    policy_ent_coeff=5e-5,
                    stop_entropy_gradient=True,
                    center_adv=False,)

    trainer.setup(algo, env)
    trainer.train(n_epochs=epochs,
                  batch_size=rollouts_per_task * env.spec.max_episode_length)


maml_trpo_metaworld_ml10()