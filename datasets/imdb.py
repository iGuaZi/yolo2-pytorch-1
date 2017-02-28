import os
import PIL
import numpy as np
from torch.multiprocessing import Pool
from torchvision import transforms


def mkdir(path, max_depth=3):
    parent, child = os.path.split(path)
    if not os.path.exists(parent) and max_depth > 1:
        mkdir(parent, max_depth-1)

    if not os.path.exists(path):
        os.mkdir(path)


class ImageDataset(object):
    def __init__(self, name, datadir, batch_size, processes=3, shuffle=True):
        self._name = name
        self._data_dir = datadir
        self._batch_size = batch_size
        self._epoch = 0
        self._num_classes = 0
        self._classes = []

        # load by self.load_dataset()
        self._image_indexes = []
        self._image_names = []
        self._annotations = []
        # Use this dict for storing dataset specific config options
        self.config = {}

        # Pool
        self._shuffle = shuffle
        self._pool_processes = processes
        self.pool = Pool(self._pool_processes)
        self.gen = None
        self.im_processor = None

    def next_batch(self):
        batch = {'images': [], 'gt_boxes': [], 'classes': [], 'dontcare': []}
        i = 0
        while i < self.batch_size:
            try:
                images, gt_boxes, classes, dontcare = self.gen.next()
                batch['images'].append(images)
                batch['gt_boxes'].append(gt_boxes)
                batch['classes'].append(classes)
                batch['dontcare'].append(dontcare)
                i += 1
            except (StopIteration, AttributeError):
                indexes = np.arange(len(self.image_names), dtype=np.int)
                if self._shuffle:
                    np.random.shuffle(indexes)
                self.gen = self.pool.imap(self.im_processor,
                                          ([self.image_names[i], self.annotations[i]] for i in indexes),
                                          chunksize=self.batch_size)
                self._epoch += 1
        batch['images'] = np.asarray(batch['images'])

        return batch

    def close(self):
        self.pool.close()
        self.pool.join()
        self.gen = None

    def load_dataset(self):
        raise NotImplementedError

    def evaluate_detections(self, all_boxes, output_dir=None):
        """
        all_boxes is a list of length number-of-classes.
        Each list element is a list of length number-of-images.
        Each of those list elements is either an empty list []
        or a numpy array of detection.

        all_boxes[class][image] = [] or np.array of shape #dets x 5
        """
        raise NotImplementedError

    @property
    def name(self):
        return self._name

    @property
    def num_classes(self):
        return len(self._classes)

    @property
    def classes(self):
        return self._classes

    @property
    def image_names(self):
        return self._image_names

    @property
    def image_indexes(self):
        return self._image_indexes

    @property
    def annotations(self):
        return self._annotations

    @property
    def cache_path(self):
        cache_path = os.path.join(self._data_dir, 'cache')
        mkdir(cache_path)
        return cache_path

    @property
    def num_images(self):
        return len(self.image_names)

    @property
    def epoch(self):
        return self._epoch

    @property
    def batch_size(self):
        return self._batch_size

    @property
    def batch_per_epoch(self):
        return self.num_images // self.batch_size


