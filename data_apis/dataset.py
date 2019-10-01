import torch
from torch.utils.data import Dataset
import numpy as np


class CVAEDataset(Dataset):
    @staticmethod
    def slice_and_pad(sent, max_len, pad_token_idx, do_pad=True):
        if len(sent) >= max_len:
            return sent[0:max_len-1] + [sent[-1]], max_len
        elif do_pad:
            return sent + [pad_token_idx] * (max_len-len(sent)), len(sent)
        else:
            return sent, len(sent)

    def __init__(self, name, data, meta_data, language, config):
        assert len(data) == len(meta_data)
        self.name = name
        self.data_lens = [len(line) for line in data]

        self.pad_token_idx = 0
        self.utt_per_case = config["utt_per_case"]
        self.max_utt_size = config['max_utt_len']
        self.is_inference = config.get("inference", False)
        print("Max len %d and min len %d and avg len %f" % (np.max(self.data_lens),
                                                            np.min(self.data_lens ),
                                                            float(np.mean(self.data_lens ))))
        self.indexes = list(np.argsort(self.data_lens))

        self.data = []
        self.meta_data = []

        for data_point_idx, data_point in enumerate(data):
            data_lens = len(data_point)
            meta_row = meta_data[data_point_idx]
            vec_a_meta, vec_b_meta, topic = meta_row
            if self.is_inference:
                end_idx_offset_start = data_lens
                end_idx_offset_end = data_lens + 1
            else:
                end_idx_offset_start = 2
                end_idx_offset_end = data_lens

            for end_idx_offset in range(end_idx_offset_start, end_idx_offset_end):
                data_item = {}

                start_idx = max(0, end_idx_offset - self.utt_per_case)
                end_idx = end_idx_offset
                cut_row = data_point[start_idx:end_idx]
                in_row = cut_row[0:-1]
                out_row = cut_row[-1]
                out_utt, out_floor, out_feat = out_row

                data_item["topics"] = torch.LongTensor([topic])

                if out_floor == 1: #B
                    data_item["my_profile"] = torch.FloatTensor(vec_b_meta)
                    data_item["ot_profile"] = torch.FloatTensor(vec_a_meta)
                else:
                    data_item["my_profile"] = torch.FloatTensor(vec_a_meta)
                    data_item["ot_profile"] = torch.FloatTensor(vec_b_meta)

                data_item["context_lens"] = torch.LongTensor([len(cut_row) - 1])
                context_utts = np.zeros((self.utt_per_case, self.max_utt_size))

                padded_utt_pairs = [self.slice_and_pad(utt, self.max_utt_size,
                                                       self.pad_token_idx)
                                    for utt, floor, feat in in_row]

                padded_utts = [utt_pair[0] for utt_pair in padded_utt_pairs]

                context_utts[0:len(in_row)] = padded_utts

                in_row_lens = np.zeros(self.utt_per_case)
                in_row_lens[0:len(in_row)] = [utt_pair[1] for utt_pair in padded_utt_pairs]

                data_item["context_utts"] = torch.LongTensor(context_utts)

                floors = np.zeros(self.utt_per_case)
                floors[0:len(in_row)] = [int(floor == out_floor) for utt, floor, feat in in_row]

                data_item["floors"] = torch.LongTensor(floors)

                padded_out_utt2 = self.slice_and_pad(out_utt, self.max_utt_size,
                                                     self.pad_token_idx)
                data_item["out_utts"] = torch.LongTensor(padded_out_utt2[0])
                data_item["out_lens"] = torch.LongTensor([padded_out_utt2[1]])
                data_item["out_floor"] = torch.LongTensor([out_floor])
                if language == "kor":
                    data_item["out_das"] = torch.LongTensor([out_feat])
                elif language == "eng":
                    data_item["out_das"] = torch.LongTensor([out_feat[0]])
                self.data.append(data_item)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]