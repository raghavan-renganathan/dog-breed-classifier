# Copyright 2017 Raghavan Renganathan, Gokul Anandhanarayanan.
# All rights reserved.
#
# Licensed under the MIT License;
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""The training process for the Dog-Breed Classification problem

Accuracy:
17%

Speed: With batch_size 32.

System              | Step Time (sec/batch)  |     Accuracy(Top 10)
------------------------------------------------------------------
1 GeForce GTX 1050  | 0.5sec/batch           | 15.4%

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime
import time
import os

import tensorflow as tf

import read_image_to_binary
import build_model

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.logging.set_verbosity(tf.logging.ERROR)

parser = build_model.parser

parser.add_argument('--train_dir', type=str, default='tmp/build_model_train',
                    help='Directory where to write event logs and checkpoint.')

parser.add_argument('--max_steps', type=int, default=100000,
                    help='Number of batches to run.')

parser.add_argument('--log_device_placement', type=bool, default=False,
                    help='Whether to log device placement.')

parser.add_argument('--log_frequency', type=int, default=100,
                    help='How often to log results to the console.')


def train():
    """Train the model for a number of steps."""
    with tf.Graph().as_default():
        global_step = tf.train.get_or_create_global_step()

        # Loading the images and labels for the model.
        # Force input pipeline to CPU:0 to avoid operations sometimes ending up
        # on GPU and resulting in a slow down.
        with tf.device('/cpu:0'):
            images, labels = build_model.distorted_inputs()

        # Build a Graph that computes the logits predictions from the
        # inference model.
        logits = build_model.generate_model(images)

        # Calculate loss.
        loss = build_model.loss(logits, labels)

        # Build a Graph that trains the model with one batch of examples and
        # updates the model parameters.
        train_op = build_model.train(loss, global_step)

        class _LoggerHook(tf.train.SessionRunHook):
            """Logs loss and runtime."""
            
            def __init__(self):
                self._step = None
                self._start_time = None
                self._saver = None

            def begin(self):
                self._step = -1
                self._start_time = time.time()
                self._saver = tf.train.Saver()

            def after_create_session(self, session, coord):
                # Restore all the variables to this session if existing
                # model was saved
                ckpt = tf.train.get_checkpoint_state(FLAGS.train_dir)
                if ckpt and ckpt.model_checkpoint_path:
                    # Restores from checkpoint
                    self._saver.restore(session, ckpt.model_checkpoint_path)
                    self._step = int(ckpt.model_checkpoint_path[-1])

            def before_run(self, run_context):
                self._step += 1
                return tf.train.SessionRunArgs(loss)  # Asks for loss value.

            def after_run(self, run_context, run_values):
                if self._step % FLAGS.log_frequency == 0:
                    current_time = time.time()
                    duration = current_time - self._start_time
                    self._start_time = current_time

                    loss_value = run_values.results
                    examples_per_sec = \
                        FLAGS.log_frequency * FLAGS.batch_size / duration
                    sec_per_batch = float(duration / FLAGS.log_frequency)

                    format_str = (
                        '%s: step %d, loss = %.2f (%.1f examples/sec; %.3f '
                        'sec/batch)')
                    print(format_str % (datetime.now(), self._step, loss_value,
                                        examples_per_sec, sec_per_batch))

        with tf.train.MonitoredTrainingSession(
                checkpoint_dir=FLAGS.train_dir,
                hooks=[tf.train.StopAtStepHook(last_step=FLAGS.max_steps),
                       tf.train.NanTensorHook(loss),
                       _LoggerHook()],
                config=tf.ConfigProto(
                    log_device_placement=FLAGS.log_device_placement)) as sess:
            while not sess.should_stop():
                sess.run(train_op)


def main(argv=None):
    read_image_to_binary.check_for_binary_data()
    if not tf.gfile.Exists(FLAGS.train_dir):
        tf.gfile.MakeDirs(FLAGS.train_dir)
    train()


if __name__ == '__main__':
    FLAGS = parser.parse_args()
    tf.app.run()
