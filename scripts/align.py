__author__ = 'anushabala'
from argparse import ArgumentParser
import math
from events import is_int, RelativeEventSequence, AbsoluteEventSequence, CursorEventSequence
from itertools import chain, combinations, permutations

numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
directions = ['x', 'y']


def is_adjacent_relative(next_action, axis='x'):
    next_x = next_action[1]
    next_y = next_action[2]

    if axis == 'y' and math.fabs(next_x) == 1 and next_y == 0:
        return True
    elif axis == 'x' and math.fabs(next_y) == 1 and next_x == 0:
        return True

    return False


def is_adjacent_absolute(next_action, prev_action, axis='x'):
    next_x = next_action[1]
    next_y = next_action[2]
    prev_x = prev_action[1]
    prev_y = prev_action[2]

    if axis == 'y' and math.fabs(next_x - prev_x) == 1 and math.fabs(next_y - prev_y) == 0:
        return True
    elif axis == 'x' and math.fabs(next_y - prev_y) == 1 and math.fabs(next_x - prev_x) == 0:
        return True

    return False

def find_consecutive_actions(actions, start_idx, sequence_type="relative"):
    # starting from start_idx, count each action that places a block adjacent to the last block placed
    # in the SAME direction
    consecutive_tokens = []
    for axis in directions:
        ctr = 1  # number of consecutive tokens always includes the first one
        prev_action = actions[start_idx]
        i = start_idx + 1
        if sequence_type == "cursor":
            if ['START'] in actions:
                i = actions.index(['START']) + 1
            else:
                i = actions.index(['BLOCK']) + 1
        while i < len(actions):
            if sequence_type == "relative" and is_adjacent_relative(actions[i], axis):
                ctr += 1
            elif sequence_type == "absolute" and is_adjacent_absolute(actions[i], prev_action, axis):
                ctr += 1
                prev_action = actions[i]
            elif sequence_type == "cursor" and 'BLOCK' in actions[i+1]:
                ctr += 1
                i += 2
            else:
                break
        consecutive_tokens.append(ctr)

    return max(consecutive_tokens)


def find_last_cursor_index(actions, start_idx, num_actions):
    ctr = 0
    idx = start_idx
    for action in actions[start_idx:]:
        if 'START' in action or 'BLOCK' in action:
            ctr += 1
            if ctr == num_actions:
                idx += 1
                break
        idx += 1
    return idx


def find_numbers(sentence):
    nums = list()
    tokens = sentence.split()
    for token in tokens:
        if token in numbers.keys():
            nums.append(numbers[token])
        elif is_int(token):
            nums.append(int(token))

    return nums


def is_repeat_instruction(sentence):
    return True if "repeat" in sentence else False


# todo (anushabala) complete this to use combinations of numbers in sentences while creating an alignment
# e.g. if the sentence has 1 and 3, return all possible permutations of everything in the powerset of (1,3)
def find_actions_per_sentence(sentence):
    nums = find_numbers(sentence)
    possible_combinations = [list(combination) for combination in chain.from_iterable(combinations(nums, i)
                                                                                      for i in range(len(nums) + 1))]
    perms = [p for combo in possible_combinations for p in permutations(combo)]
    return set(perms)


def find_segmentations(sentences, current_path, paths, total_actions):
    if not sentences:
        if sum(current_path) == total_actions:
            paths.append(current_path)
        return

    nums = find_numbers(sentences[0])
    if not nums:
        nums.append(1)
    if is_repeat_instruction(sentences[0]) and current_path and current_path[-1] not in nums:
        nums.append(current_path[-1])
    for num in nums:
        new_path = list(current_path)
        new_path.append(num)
        find_segmentations(sentences[1:], new_path, paths, total_actions)


# todo (anushabala) complete this to use combinations of numbers in sentences while creating an alignment
def better_align(sentences, actions):
    segmentations = []
    find_segmentations(sentences, [], segmentations, len(actions))
    sentence_alignments = []

    for path in segmentations:
        action_idx = 0
        alignment = []
        for (i, action_group) in enumerate(path):
            aligned_actions = []
            for num_actions in action_group:
                if num_actions == 1:
                    aligned_actions.append(actions[action_idx:action_idx + num_actions])
                    action_idx += 1
                else:
                    num_consecutive_actions = find_consecutive_actions(actions, action_idx)
                    if num_actions <= num_consecutive_actions:
                        aligned_actions.append(actions[action_idx:action_idx + num_actions])
                        action_idx += num_actions

                    else:
                        aligned_actions = None
                        break
            if not aligned_actions:
                alignment = None
                break
            else:
                alignment.append((sentences[i], aligned_actions))
        if alignment:
            sentence_alignments.append((alignment, path))

    if not sentence_alignments:
        return 0, None, None
    scored_alignments = [(score_smart_alignment(alignment, path), alignment, path) for (alignment, path) in
                         sentence_alignments]
    return max(scored_alignments, key=lambda x: x[0])


def heuristic_align(sentences, actions, sequence_type="relative"):
    segmentations = []
    max_actions = actions.count(["BLOCK"]) + 1 if sequence_type == "cursor" else len(actions)
    find_segmentations(sentences, [], segmentations, max_actions)
    sentence_alignments = []
    for path in segmentations:
        action_idx = 0
        alignment = []

        for (i, num_actions) in enumerate(path):
            if sequence_type == "cursor":
                end_idx = find_last_cursor_index(actions, action_idx, num_actions)
                aligned_actions = actions[action_idx: end_idx]
                action_idx = end_idx
            else:
                aligned_actions = actions[action_idx:action_idx + num_actions]
                action_idx += num_actions
            alignment.append((sentences[i], aligned_actions))
        if alignment:
            sentence_alignments.append((alignment, path))

    if not sentence_alignments:
        return 0, None, None
    scored_alignments = [(score_alignment(alignment, sequence_type), alignment, path) for (alignment, path) in
                         sentence_alignments]
    return max(scored_alignments, key=lambda x: x[0])


# todo (anushabala) complete this to score alignments made by finding combinations of numbers in sentences
def score_smart_alignment(alignment, path):
    score = 0
    prev_actions = -1
    for (idx, (sentence, aligned_actions)) in enumerate(alignment):
        nums = find_numbers(sentence)

        if is_repeat_instruction(sentence):
            score = score + 1 if len(aligned_actions) == prev_actions else score - 1
        elif not nums:
            score = score + 1 if len(aligned_actions) == 1 else score - 1
        else:
            for num_actions in path[idx]:
                score = score + 1 if num_actions in nums else score - 1
        prev_actions = len(aligned_actions)

    return score


def score_alignment(alignment, sequence_type="relative"):
    alignment_score = 0
    prev_actions = -1
    for (idx, (sentence, aligned_actions)) in enumerate(alignment):
        num_aligned_actions = len(aligned_actions)
        if sequence_type == "cursor":
            num_aligned_actions = 0
            if ['BLOCK'] in aligned_actions:
                num_aligned_actions += aligned_actions.count(['BLOCK'])
            if ['START'] in aligned_actions:
                num_aligned_actions += 1
        if is_repeat_instruction(sentence):
            alignment_score = alignment_score + 1 if num_aligned_actions == prev_actions else alignment_score - 1

        num_consecutive_actions = find_consecutive_actions(aligned_actions, 0, sequence_type)
        alignment_score = alignment_score + 1 if num_aligned_actions <= num_consecutive_actions else alignment_score - 1
        prev_actions = num_aligned_actions
    return alignment_score


def naive_align(sentences, actions):
    actions_per_alignment = len(actions) / len(sentences)
    alignments = []
    for (idx, sentence) in enumerate(sentences):
        start_idx = idx * actions_per_alignment
        # if it's the last sentence, align all remaining actions to it
        end_idx = (idx + 1) * actions_per_alignment if idx != len(sentences) - 1 else len(actions)

        aligned_actions = actions[start_idx:end_idx]
        alignments.append((sentence, aligned_actions))

    return alignments


def actions_to_str(actions):
    return " ".join([" ".join(map(str, l)) for l in actions])


def write_examples(alignments, output_file):
    for aligned_example in alignments:
        aligned_sentences = [example[0] for example in aligned_example]
        aligned_actions = [example[1] for example in aligned_example]

        for sentence in aligned_sentences[:-1]:
            output_file.write("%s | " % sentence)
        output_file.write("%s\t" % aligned_sentences[-1])
        for action in aligned_actions[:-1]:
            output_file.write("%s | " % actions_to_str(action))
        output_file.write("%s\n" % actions_to_str(aligned_actions[-1]))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-tsv", type=str, required=True, help="Path to TSV containing input and output sequences")
    parser.add_argument("-output", type=str, required=True, help="Path to file to write alignments to")
    parser.add_argument("-alignment_type", type=str, default="clever", help="Type of algorithm to use for alignments."
                                                                            "(either 'silly' or 'clever'. Defaults to clever")
    parser.add_argument("-sequence_type", type=str, default="relative", help="Format of data (either one of 'relative' "
                                                                             ",'absolute', or 'cursor'. Defaults to relative.")
    parser.add_argument("-bitmap_dim", type=int, default=25, help="Width of bitmap (assumed square)")
    args = parser.parse_args()
    infile = open(args.tsv, 'Ur')
    raw_data = [line.strip().split("\t") for line in infile.readlines()]
    all_alignments = []
    positive_score = 0
    neg_score = 0
    if args.sequence_type == "cursor":
        directions = ["x"]
    for (command_sequence, action_sequence) in raw_data:
        sentences = command_sequence.strip().split(" . ")
        if args.sequence_type == "absolute":
            event_sequence = AbsoluteEventSequence.from_string(action_sequence)
        elif args.sequence_type == "cursor":
            relative_sequence = RelativeEventSequence.from_eval_str(action_sequence)
            abs_sequence = AbsoluteEventSequence.from_relative(relative_sequence, args.bitmap_dim, args.bitmap_dim)
            event_sequence = CursorEventSequence.from_absolute(abs_sequence)
        else:
            event_sequence = RelativeEventSequence.from_eval_str(action_sequence)
        actions = event_sequence.events
        alignments = []
        if args.alignment_type == "silly":
            alignments = naive_align(sentences, actions)
        elif args.alignment_type == "clever":
            (score, alignments, path) = heuristic_align(sentences, actions, args.sequence_type)
            if score >= len(sentences) - 4 and alignments:
                positive_score += 1
                all_alignments.append(alignments)
            elif score < len(sentences) - 4 and alignments:
                neg_score += 1

    print "(%d/%d) with score > (# of sentences - 4)" % (positive_score, len(raw_data))
    print "(%d/%d) with score < (# of sentences - 4)" % (neg_score, len(raw_data))
    outfile = open(args.output, 'w')
    write_examples(all_alignments, outfile)
