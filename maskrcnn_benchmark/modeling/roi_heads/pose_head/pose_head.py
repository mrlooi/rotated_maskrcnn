import torch
from torch import nn

from maskrcnn_benchmark.structures.bounding_box import BoxList

from .roi_pose_feature_extractors import make_roi_pose_feature_extractor
from .roi_pose_predictors import make_roi_pose_predictor
from .inference import make_roi_pose_post_processor
from .loss import make_roi_pose_loss_evaluator

from maskrcnn_benchmark.modeling.roi_heads.mask_head.mask_head import keep_only_positive_boxes


class ROIPoseHead(torch.nn.Module):
    def __init__(self, cfg):
        super(ROIPoseHead, self).__init__()
        self.cfg = cfg.clone()
        self.feature_extractor = make_roi_pose_feature_extractor(cfg)
        self.predictor = make_roi_pose_predictor(cfg)
        self.post_processor = make_roi_pose_post_processor(cfg)
        self.loss_evaluator = make_roi_pose_loss_evaluator(cfg)

    def forward(self, features, proposals, targets=None):
        """
        Arguments:
            features (list[Tensor]): feature-maps from possibly several levels
            proposals (list[BoxList]): proposal boxes
            targets (list[BoxList], optional): the ground-truth targets.

        Returns:
            x (Tensor): the result of the feature extractor
            proposals (list[BoxList]): during training, the original proposals
                are returned. During testing, the predicted boxlists are returned
                with the `vertex` field set
            losses (dict[Tensor]): During training, returns the losses for the
                head. During testing, returns an empty dict.
        """

        if self.training:
            # during training, only focus on positive boxes
            # all_proposals = proposals
            proposals, positive_inds = keep_only_positive_boxes(proposals)
        if self.training and self.cfg.MODEL.ROI_POSE_HEAD.SHARE_BOX_FEATURE_EXTRACTOR:
            x = features
            x = x[torch.cat(positive_inds, dim=0)]
        else:
            x = self.feature_extractor(features, proposals)
        pred_pose = self.predictor(x)

        if not self.training:
            result = self.post_processor(pred_pose, proposals)
            return x, pred_pose, result, {}

        loss_pose = self.loss_evaluator(proposals, pred_pose, targets)

        return x, pred_pose, proposals, dict(loss_pose=loss_pose)


def build_roi_pose_head(cfg):
    return ROIPoseHead(cfg)