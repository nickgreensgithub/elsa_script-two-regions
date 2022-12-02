import pandas as pd
import argparse
import os
from itertools import chain


def read_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path')
    parser.add_argument('-f', '--result_file_name', default="joined", required=False, help="The name of the resulting file, will have the same extension as the input files")
    parser.add_argument('-s', '--column_separator', default=None, required=False)
    args = parser.parse_args()
    return args


def unescaped_str(arg_str: str) -> str:
    if arg_str.startswith('\\'):
        return arg_str.removeprefix('\\')
    return arg_str


def read_file(path: str, col_separator='\t') -> pd.DataFrame:
    df = pd.read_csv(path, sep=col_separator, header=None, index_col=False, engine='python')
    return df


def write_file(df: pd.DataFrame, path: str, col_separator='\t') -> None:
    df.to_csv(path, sep=col_separator, index=False, header=False)


def unify_ranges(df: pd.DataFrame) -> list[list[int]]:
    ranges = df.apply(axis='columns', func=lambda row: [row[2], row[3]]).to_list()
    return get_union_of_ranges(ranges)


def get_union_of_ranges(ranges: list[list[int, int]]) -> list[list[int]]:
    # Assumes that ranges are already sorted
    unified_ranges = []
    for begin, end in ranges:
        if unified_ranges and unified_ranges[-1][1] >= begin - 1:
            unified_ranges[-1][1] = max(unified_ranges[-1][1], end)
        else:
            unified_ranges.append([begin, end])
    return unified_ranges


def find_fillable_gaps(range_min: int, range_max: int, ranges: list[list[int, int]]):
    ranges = sorted(ranges)
    flat = chain((range_min - 1,), chain.from_iterable(ranges), (range_max + 1,))
    return [[x+1, y-1] for x, y in zip(flat, flat) if x+1 < y]


def get_row_start(row: pd.Series) -> int:
    return row.iloc[2]


def get_row_stop(row: pd.Series) -> int:
    return row.iloc[3]


def adjust_end_positions(df:pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame.copy(df)
    max_index = df.shape[1] - 1
    for index, row in df.iterrows():
        if index < max_index:
            current_stop = get_row_stop(row)
            next_start = get_row_start(df.iloc[index+1])
            if current_stop >= next_start:
                row.iloc[3] = next_start - 1
            result.iloc[index] = row
    return result


def populate_gaps(trimmed_segments: pd.DataFrame, original_segments: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    results = pd.DataFrame.copy(trimmed_segments)
    new_segments = list()
    trimmed_segments.reset_index(drop=True, inplace=True)
    for index, row in gaps.iterrows():
        gap_start = row[2]
        gap_stop = row[3]
        comparison_segments = original_segments.loc[(original_segments[3] >= gap_start) & (original_segments[2] <= gap_stop)]
        for comparison_index, comparison_segment in comparison_segments.iterrows():
            gap_start = row[2]
            if comparison_segment[3] >= gap_stop:
                new_segment = pd.Series.copy(comparison_segment)
                new_segment.iloc[3] = gap_stop
                new_segment.iloc[2] = gap_start
                new_segments.append(new_segment)
                gaps.iloc[index][2] = comparison_segment[3] + 1
                continue
            else:
                new_segment = pd.Series.copy(comparison_segment)
                new_segment.iloc[2] = gap_start
                new_segments.append(new_segment)
                gaps.iloc[index][2] = comparison_segment[3] + 1
    results = pd.concat([results, pd.DataFrame(new_segments, columns=results.columns)])
    return results


def create_segments_from_gaps(gaps: list[list[int, int]]) -> pd.DataFrame:
    result = pd.DataFrame(columns=[0, 1, 2, 3])

    for gap in gaps:
        result = pd.concat([result, pd.DataFrame([[pd.NA, pd.NA, gap[0], gap[1]]], columns=result.columns)])
    return result


def main() -> None:
    args = read_args()
    input_file = args.file_path
    result_file_name = args.result_file_name
    column_separator = args.column_separator

    if not os.path.exists(input_file):
        print("File path does not exist")
        exit(1)

    df = read_file(input_file, column_separator)
    df_conserved_regions = df.loc[df[1] == 'CR']  # Assuming we don't need this since CR just fills everything
    df_other_regions = df.loc[df[1] != 'CR']
    df_other_regions.reset_index(drop=True, inplace=True)

    unified_ranges = unify_ranges(df_other_regions)
    region_start = df.iloc[0][2]
    region_end = max(df.iloc[df.shape[1]][3], df.iloc[0][3])

    shortened_segments = adjust_end_positions(df_other_regions)
    gaps = find_fillable_gaps(region_start, region_end, unify_ranges(shortened_segments))
    segmented_gaps = create_segments_from_gaps(gaps)
    fill_gaps_result = populate_gaps(shortened_segments, df_other_regions, segmented_gaps)

    cr_gaps = find_fillable_gaps(region_start, region_end, unified_ranges)
    segmented_cr_gaps = create_segments_from_gaps(cr_gaps)

    # Fill all the remaining gaps with CR
    segmented_cr_gaps[1] = 'CR'
    segmented_cr_gaps[0] = df.iloc[0][0]

    # Combine the results
    result = pd.concat([fill_gaps_result, segmented_cr_gaps])
    result.sort_values(by=[2], inplace=True)

    result.to_csv(result_file_name, sep='\t', header=False, index=False)


if __name__ == "__main__":
    main()
