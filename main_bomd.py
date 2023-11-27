import os
import sys

import wandb
from loguru import logger

from data.cx14_dataloader_cut import construct_cx14_cut
from data.cx14_pdc_dataloader_cut import construct_cx14_pdc_cut
from data.cxp_dataloader_cut import construct_cxp_cut
from opts import parse_args
from trainer.bomd_trainer import BoMD
from utils.utils import color, sanity_check

BRED = color.BOLD + color.RED


def config_wandb(args):

    os.environ["WANDB_MODE"] = args.wandb_mode

    if args.add_noise:
        EXP_NAME = f"{args.train_data}-BoMD-NOISE"
        args.run_name = "[{}][{}|{}][{}]_A2S[topk={}|mixup={}|beta={}]".format(
            args.bert_name.upper(),
            str(args.noise_ratio)[1:],
            str(args.noise_p)[1:],
            args.enhance_dist,
            args.nsd_topk,
            args.lam,
            args.beta,
        )
    else:
        EXP_NAME = f"{args.train_data}-BoMD"
        args.run_name = "[{}][{}]_A2S[topk={}|mixup={}|beta={}]".format(
            args.bert_name.upper(),
            args.enhance_dist,
            args.nsd_topk,
            args.lam,
            args.beta,
        )
    wandb.init(project=EXP_NAME, notes=args.run_note, name=args.run_name)

    config = wandb.config
    config.update(args)
    logger.bind(stage="CONFIG").critical("NAME = {}".format(args.run_name))
    logger.bind(stage="CONFIG").critical("WANDB_MODE = {}".format(args.wandb_mode))
    logger.bind(stage="CONFIG").info("Experiment Name: {}".format(EXP_NAME))
    return


def load_args():
    args = parse_args()
    # set_random_seeds(args.seed)
    # args.batch_size = 16
    # args.num_workers = 12
    # args.use_ensemble = False
    # args.trim_data = True
    # args.num_classes = 14
    # args.lr_mid = 1e-4
    # args.lr_cls = 0.05
    # args.epochs_cls = 30
    # args.total_runs = 1
    # args.wandb_mode = "online"
    # args.num_fea = 1
    # args.run_note = ""
    logger.bind(stage="CONFIG").critical(
        f"use_ensemble = {str(args.use_ensemble)} || num_fea = {args.num_fea}"
    )
    return args


def main():
    args = load_args()
    print(args)
    config_wandb(args)
    try:
        os.mkdir(args.save_dir)
    except OSError as error:
        logger.bind(stage="CONFIG").debug(error)

    log_file = open(os.path.join(wandb.run.dir, "loguru.txt"), "w")
    logger.add(log_file, enqueue=True)

    if args.add_noise:
        construct_func = construct_cx14_pdc_cut

    if args.train_data == "NIH":
        construct_func = construct_cx14_cut
    else:
        construct_func = construct_cxp_cut

    """
    NIH
    """
    train_loader_val = construct_func(
        args, mode="train", file_name="train", stage="MID"
    )
    static_train_loader = construct_func(
        args, mode="test", file_name="train", stage="STATIC"
    )
    train_loader_cls = construct_func(
        args, mode="train", file_name="train", stage="CLS"
    )

    sanity_check(train_loader_val, static_train_loader, train_loader_cls)

    # args.load_mid_features = True
    # args.load_sample_graph = True

    sgval_runner = BoMD(args, train_loader_val, static_train_loader, train_loader_cls)
    sgval_runner.deploy()

    # sgval_runner.a2s_runner.run()
    # sgval_runner.cls_runner.train_loader.dataset.knn = np.load(
    #     os.path.join(wandb.run.dir, "knn.npy")
    # )
    # # sgval_runner.cls_runner.train_loader.dataset.knn = np.load(
    # #     os.path.join("./wandb", args.mid_ckpt, "files", "knn.npy")
    # # )
    # logger.bind(stage="GLOBAL").critical(f"CLS")
    # sgval_runner.cls_runner.run()

    wandb.finish()
    return


if __name__ == "__main__":

    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS} </green> | <bold><cyan> [{extra[stage]}] </cyan></bold> | <level>{level: <8}</level> | <level>{message}</level>"
    logger.remove()
    logger.add(sys.stderr, format=fmt)
    main()
