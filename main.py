from typing import Optional
import pandas as pd
import argparse
import os


class Sequence:

    def __init__(self, label: str, name: str, start: int, end: int):
        self.name = name
        self.label = label
        self.start = start
        self.end = end
        self.original_end = end

    def __str__(self):
        return f"{self.label}\t{self.name}\t{self.start}\t{self.end}\n"

    def __overlaps(self, other: "Sequence") -> bool:
        return self.start < other.end and other.start < self.original_end

    def get_sequence_overlap(self, other: "Sequence") -> Optional[tuple[int, int]]:
        if self.__overlaps(other):
            return max(self.start, other.start), min(self.original_end, other.end)
        else:
            # no overlap
            return None

    def set_new_end(self, new_end: int):
        self.end = new_end


def create_gap_sequences(sequences: list[Sequence], range_start: int, range_end: int) -> list[Sequence]:
    gaps = list[Sequence]()
    first_sequence = sequences[0]
    last_sequence = sequences[-1]
    if first_sequence.start > range_start:
        gaps.append(Sequence("GAP", "GAP", range_start, first_sequence.start - 1))
    if last_sequence.end < range_end:
        gaps.append(Sequence("GAP", "GAP", last_sequence.end + 1, range_end))

    for index, sequence in enumerate(sequences):
        last_sequence = sequences[index - 1]
        if last_sequence and last_sequence.end < (sequence.start - 1):
            gaps.append(Sequence("GAP", "GAP", (last_sequence.end + 1), (sequence.start - 1)))

    return gaps


def populate_gaps(gaps: list[Sequence], sequences: list[Sequence]):
    gap_fillers = list[Sequence]()
    unfillable_gaps = list[Sequence]()

    i = 0
    while i < len(gaps):
        gap = gaps.pop(0)
        filled = False
        for sequence in sequences:
            overlap = sequence.get_sequence_overlap(gap)
            if overlap:
                filled = True
                gap_filler = Sequence(sequence.label, sequence.name, overlap[0], overlap[1])
                gap_fillers.append(gap_filler)
                if overlap != (gap.start, gap.end):
                    gaps.extend(create_gap_sequences([gap_filler], gap.start, gap.end))
        if not filled:
            unfillable_gaps.append(gap)
    return gap_fillers, unfillable_gaps


def adjust_sequence_ends_to_fit_together(sequences: list[Sequence]):
    for index in range(1, len(sequences)):  # Starting from 2nd sequence(so there's a previous one)
        sequence = sequences[index]
        previous_sequence = sequences[index - 1]
        if previous_sequence and (previous_sequence.end >= sequence.start - 1):
            previous_sequence.set_new_end(sequence.start - 1)


def read_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path')
    parser.add_argument('-f', '--result_file_name', default="joined", required=False, help="The name of the resulting file")
    parser.add_argument('-s', '--column_separator', default='\t', required=False)
    args = parser.parse_args()
    return args


def read_file(path: str, col_separator='\t') -> pd.DataFrame:
    df = pd.read_csv(path, sep=col_separator, header=None, index_col=False, engine='python')
    return df


def get_region_end(df: pd.DataFrame) -> int:
    return max(df[3])


# TODO refactor this part
def main() -> None:
    args = read_args()
    input_file = args.file_path
    result_file_name = args.result_file_name
    column_separator = args.column_separator

    if not os.path.exists(input_file):
        print("File path does not exist")
        exit(1)

    df = read_file(input_file, column_separator)
    df_conserved_regions = df.loc[df[1] == 'CR']
    df_other_regions = df.loc[df[1] != 'CR']
    conserved_regions = [(Sequence(row[0], row[1], row[2], row[3])) for index, row in df_conserved_regions.iterrows()]
    other_regions = [(Sequence(row[0], row[1], row[2], row[3])) for index, row in df_other_regions.iterrows()]
    region_start = df.iloc[0][2]
    region_end = get_region_end(df)
    adjust_sequence_ends_to_fit_together(other_regions)
    gaps = create_gap_sequences(other_regions, region_start, region_end)

    filler_sequences, actual_gaps = populate_gaps(gaps, other_regions)
    cr_sequences, problem_gaps = populate_gaps(actual_gaps, conserved_regions)

    if problem_gaps:
        print("Could not fill all gaps")

    results = filler_sequences + other_regions + cr_sequences
    results.sort(key=lambda x: x.start)

    with open(result_file_name, 'w') as result_file:
        for result in results:
            result_file.write(str(result))


if __name__ == "__main__":
    main()
