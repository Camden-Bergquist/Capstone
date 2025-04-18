use crate::{Board, FallingPiece, Piece, PieceState, RotationState, Row, TspinStatus};
use crate::lock_data::{LockResult, PlacementKind};
use serde::*;

#[derive(Clone, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
#[serde(default)]
pub struct Standard {
    pub back_to_back: i32,
    pub bumpiness: i32,
    pub bumpiness_sq: i32,
    pub row_transitions: i32,
    pub height: i32,
    pub top_half: i32,
    pub top_quarter: i32,
    pub jeopardy: i32,
    pub cavity_cells: i32,
    pub cavity_cells_sq: i32,
    pub overhang_cells: i32,
    pub overhang_cells_sq: i32,
    pub covered_cells: i32,
    pub covered_cells_sq: i32,
    pub tslot: [i32; 4],
    pub well_depth: i32,
    pub max_well_depth: i32,
    pub well_column: [i32; 10],

    pub b2b_clear: i32,
    pub clear1: i32,
    pub clear2: i32,
    pub clear3: i32,
    pub clear4: i32,
    pub tspin1: i32,
    pub tspin2: i32,
    pub tspin3: i32,
    pub mini_tspin1: i32,
    pub mini_tspin2: i32,
    pub perfect_clear: i32,
    pub combo_garbage: i32,
    pub move_time: i32,
    pub wasted_t: i32,

    pub use_bag: bool,
    pub timed_jeopardy: bool,
    pub stack_pc_damage: bool,
    pub sub_name: Option<String>,
}

impl Default for Standard {
    fn default() -> Self {
        Standard {
            back_to_back: 52,
            bumpiness: -24,
            bumpiness_sq: -7,
            row_transitions: -5,
            height: -39,
            top_half: -150, // originally -150
            top_quarter: -511, // originally -511
            jeopardy: -11,
            cavity_cells: -173, // was originally -173.
            cavity_cells_sq: -3, // was originally -3, multiplying for testing.
            overhang_cells: -34, // originally -34
            overhang_cells_sq: -1, // originally -1
            covered_cells: -17,
            covered_cells_sq: -1,
            tslot: [8, 148, 192, 407], // originally [8, 148, 192, 407]
            well_depth: 57,
            max_well_depth: 17,
            well_column: [20, 23, 20, 50, 59, 21, 59, 10, -10, 24],

            move_time: -3,
            wasted_t: -152,
            b2b_clear: 104,
            clear1: -143,
            clear2: -100,
            clear3: -58,
            clear4: 390,
            tspin1: 121, // originally 121
            tspin2: 410, // originally 410
            tspin3: 602, // originally 602
            mini_tspin1: -158,
            mini_tspin2: -93,
            perfect_clear: 999,
            combo_garbage: 150,

            use_bag: true,
            timed_jeopardy: false, // originally True
            stack_pc_damage: false,
            sub_name: None,
        }
    }
}

impl Standard {
    pub fn fast_config() -> Self {
        Standard {
            back_to_back: 10,
            bumpiness: -7,
            bumpiness_sq: -28,
            row_transitions: -5,
            height: -46,
            top_half: -126,
            top_quarter: -493,
            jeopardy: -11,
            cavity_cells: -176,
            cavity_cells_sq: -6,
            overhang_cells: -47,
            overhang_cells_sq: -9,
            covered_cells: -25,
            covered_cells_sq: 1,
            tslot: [0, 150, 296, 207],
            well_depth: 158,
            max_well_depth: -2,
            well_column: [31, 16, -41, 37, 49, 30, 56, 48, -27, 22],
            b2b_clear: 74,
            clear1: -122,
            clear2: -174,
            clear3: 11,
            clear4: 424,
            tspin1: 131,
            tspin2: 392,
            tspin3: 628,
            mini_tspin1: -188,
            mini_tspin2: -682,
            perfect_clear: 991,
            combo_garbage: 272,
            move_time: -1,
            wasted_t: -147,
            use_bag: true,
            timed_jeopardy: false,
            stack_pc_damage: false,
            sub_name: None,
        }
    }
}

/// Evaluates the bumpiness of the playfield.
fn bumpiness(board: &Board<impl Row>, well: usize) -> (i32, i32) {
    let mut bumpiness = -1;
    let mut bumpiness_sq = -1;

    let mut prev = if well == 0 { 1 } else { 0 };
    for i in 1..10 {
        if i == well {
            continue;
        }
        let dh = (board.column_heights()[prev] - board.column_heights()[i]).abs();
        bumpiness += dh;
        bumpiness_sq += dh * dh;
        prev = i;
    }

    (bumpiness.abs() as i32, bumpiness_sq.abs() as i32)
}

/// Evaluates the holes in the playfield.
fn cavities_and_overhangs(board: &Board<impl Row>) -> (i32, i32) {
    let mut cavities = 0;
    let mut overhangs = 0;

    for y in 0..*board.column_heights().iter().max().unwrap() {
        for x in 0..10 {
            if board.occupied(x as i32, y) || y >= board.column_heights()[x] {
                continue;
            }

            if x > 1 {
                if board.column_heights()[x - 1] <= y - 1 && board.column_heights()[x - 2] <= y {
                    overhangs += 1;
                    continue;
                }
            }

            if x < 8 {
                if board.column_heights()[x + 1] <= y - 1 && board.column_heights()[x + 2] <= y {
                    overhangs += 1;
                    continue;
                }
            }

            cavities += 1;
        }
    }

    (cavities, overhangs)
}

/// Evaluates how covered holes in the playfield are.
fn covered_cells(board: &Board<impl Row>) -> (i32, i32) {
    let mut covered = 0;
    let mut covered_sq = 0;

    for x in 0..10 {
        for y in (0..board.column_heights()[x] - 2).rev() {
            if !board.occupied(x as i32, y) {
                let cells = 6.min(board.column_heights()[x] - y - 1);
                covered += cells;
                covered_sq += cells * cells;
            }
        }
    }

    (covered, covered_sq)
}

macro_rules! detect_shape {
    (
        $name:ident
        heights [$($heights:pat)*]
        require (|$b:pat, $xarg:pat| $req:expr)
        start_y ($starty:expr)
        success ($x:expr, $y:expr, $piece:ident, $facing:ident)
        $([$($rowspec:tt)*])*
    ) => {
        fn $name<R: Row>(board: &Board<R>) -> Option<FallingPiece> {
            for (x, s) in board.column_heights().windows(
                detect_shape!(@len [$($heights)*])
            ).enumerate() {
                let x = x as i32;
                if let [$($heights),*] = *s {
                    if !(|$b: &Board<R>, $xarg: i32| $req)(board, x) { continue }
                    let y = $starty;
                    $(
                        {
                            $(
                                if !detect_shape!(@rowspec $rowspec board x y) {
                                    continue
                                }
                                #[allow(unused)]
                                let x = x + 1;
                            )*
                        }
                        #[allow(unused)]
                        let y = y-1;
                    )*
                    return Some(FallingPiece {
                        kind: PieceState(Piece::$piece, RotationState::$facing),
                        x: x + $x,
                        y: $y,
                        tspin: TspinStatus::None
                    })
                }
            }
            None
        }
    };
    (@rowspec ? $board:ident $x:ident $y:ident) => { true };
    (@rowspec # $board:ident $x:ident $y:ident) => { $board.occupied($x, $y) };
    (@rowspec _ $board:ident $x:ident $y:ident) => { !$board.occupied($x, $y) };
    (@len []) => { 0 };
    (@len [$_:tt $($rest:tt)*]) => { 1 + detect_shape!(@len [$($rest)*]) }
}

detect_shape! {
    sky_tslot_right
    heights [_ h1 h2]
    require (|_, _| h1 <= h2-1)
    start_y(h2+1)
    success(1, h2, T, South)
    [# ? ?]
    [_ ? ?]
    [# ? ?]
}

detect_shape! {
    sky_tslot_left
    heights [h1 h2 _]
    require(|_, _| h2 <= h1-1)
    start_y(h1+1)
    success(1, h1, T, South)
    [? ? #]
    [? ? _]
    [? ? #]
}

detect_shape! {
    tst_twist_left
    heights [h1 h2 _]
    require (|board, x| h1 <= h2 && board.occupied(x-1, h2) == board.occupied(x-1, h2+1))
    start_y (h2 + 1)
    success (2, h2-2, T, West)
    [? ? #]
    [? ? _]
    [? ? _]
    [? _ _]
    [? ? _]
}

detect_shape! {
    tst_twist_right
    heights [_ h1 h2]
    require (|board, x| h2 <= h1 && board.occupied(x+3, h1) == board.occupied(x+3, h1+1))
    start_y (h1 + 1)
    success (0, h1-2, T, East)
    [# ? ?]
    [_ ? ?]
    [_ ? ?]
    [_ _ ?]
    [_ ? ?]
}

detect_shape! {
    fin_left
    heights [h1 h2 _ _]
    require (|_, _| h1 <= h2+1)
    start_y(h2 + 2)
    success (3, h2-1, T, West)
    [? ? # # ?]
    [? ? _ _ ?]
    [? ? _ _ #]
    [? ? _ _ ?]
    [? ? # _ #]
}

detect_shape! {
    fin_right
    heights [_ _ h1 h2]
    require (|board, x| h2 <= h1+1 && board.occupied(x-1, h1) && board.occupied(x-1, h1-2))
    start_y (h1 + 2)
    success (0, h1-1, T, East)
    [# # ? ?]
    [_ _ ? ?]
    [_ _ ? ?]
    [_ _ ? ?]
    [_ # ? ?]
}

fn cave_tslot<R: Row>(board: &Board<R>, mut starting_point: FallingPiece) -> Option<FallingPiece> {
    starting_point.sonic_drop(board);
    let x = starting_point.x;
    let y = starting_point.y;
    match starting_point.kind.1 {
        RotationState::East => {
            // Check:
            // []<>      <>
            // ..<><>  []<><>[]
            // []<>[]    <>....
            //           []..[]
            if !board.occupied(x - 1, y)
                && board.occupied(x - 1, y - 1)
                && board.occupied(x + 1, y - 1)
                && board.occupied(x - 1, y + 1)
            {
                Some(FallingPiece {
                    x,
                    y,
                    kind: PieceState(Piece::T, RotationState::South),
                    tspin: TspinStatus::None,
                })
            } else if !board.occupied(x + 1, y - 1)
                && !board.occupied(x + 2, y - 1)
                && !board.occupied(x + 1, y - 2)
                && board.occupied(x - 1, y)
                && board.occupied(x + 2, y)
                && board.occupied(x, y - 2)
                && board.occupied(x + 2, y - 2)
            {
                Some(FallingPiece {
                    x: x + 1,
                    y: y - 1,
                    kind: PieceState(Piece::T, RotationState::South),
                    tspin: TspinStatus::None,
                })
            } else {
                None
            }
        }
        RotationState::West => {
            // Check:
            //   <>[]      <>
            // <><>..  []<><>[]
            // []<>[]  ....<>
            //         []..[]
            if !board.occupied(x + 1, y)
                && board.occupied(x + 1, y + 1)
                && board.occupied(x + 1, y - 1)
                && board.occupied(x - 1, y - 1)
            {
                Some(FallingPiece {
                    x,
                    y,
                    kind: PieceState(Piece::T, RotationState::South),
                    tspin: TspinStatus::None,
                })
            } else if !board.occupied(x - 1, y - 1)
                && !board.occupied(x - 2, y - 1)
                && !board.occupied(x - 1, y - 2)
                && board.occupied(x + 1, y)
                && board.occupied(x - 2, y)
                && board.occupied(x - 2, y - 2)
                && board.occupied(x, y - 2)
            {
                Some(FallingPiece {
                    x: x - 1,
                    y: y - 1,
                    kind: PieceState(Piece::T, RotationState::South),
                    tspin: TspinStatus::None,
                })
            } else {
                None
            }
        }
        _ => None,
    }
}

struct Cutout<R: Row> {
    lines: usize,
    result: Option<Board<R>>,
}

fn cutout_tslot<R: Row>(mut board: Board<R>, mut piece: FallingPiece) -> Cutout<R> {
    piece.tspin = TspinStatus::Full;
    let result = board.lock_piece(piece);

    match result.placement_kind {
        PlacementKind::Tspin => Cutout {
            lines: 0,
            result: None,
        },
        PlacementKind::Tspin1 => Cutout {
            lines: 1,
            result: None,
        },
        PlacementKind::Tspin2 => Cutout {
            lines: 2,
            result: Some(board),
        },
        PlacementKind::Tspin3 => Cutout {
            lines: 3,
            result: Some(board),
        },
        _ => unreachable!(),
    }
}

/// Evaluates a board based on heuristics and the most recent lock result.
impl Standard {
    pub fn evaluate_board<R: Row>(
        &self,
        board: &Board<R>,
        lock: &LockResult,
        move_time: u32,
        placed: Piece,
    ) -> (i32, i32) {
        let mut transient_eval = 0;
        let mut acc_eval = 0;

        if lock.perfect_clear {
            acc_eval += self.perfect_clear;
        }
        if !lock.perfect_clear {
            if lock.b2b {
                acc_eval += self.b2b_clear;
            }
            if let Some(combo) = lock.combo {
                let combo = combo.min(11) as usize;
                acc_eval += self.combo_garbage * crate::COMBO_GARBAGE[combo] as i32;
            }
            match lock.placement_kind {
                PlacementKind::Clear1 => {
                    acc_eval += self.clear1;
                }
                PlacementKind::Clear2 => {
                    acc_eval += self.clear2;
                }
                PlacementKind::Clear3 => {
                    acc_eval += self.clear3;
                }
                PlacementKind::Clear4 => {
                    acc_eval += self.clear4;
                }
                PlacementKind::Tspin1 => {
                    acc_eval += self.tspin1;
                }
                PlacementKind::Tspin2 => {
                    acc_eval += self.tspin2;
                }
                PlacementKind::Tspin3 => {
                    acc_eval += self.tspin3;
                }
                PlacementKind::MiniTspin1 => {
                    acc_eval += self.mini_tspin1;
                }
                PlacementKind::MiniTspin2 => {
                    acc_eval += self.mini_tspin2;
                }
                _ => {}
            }
        }

        if placed == Piece::T {
            match lock.placement_kind {
                PlacementKind::Tspin1 | PlacementKind::Tspin2 | PlacementKind::Tspin3 => {}
                _ => {
                    acc_eval += self.wasted_t;
                }
            }
        }

        let move_time = if lock.placement_kind.is_clear() {
            move_time as i32 + 40
        } else {
            move_time as i32
        };
        acc_eval += self.move_time * move_time;

        if board.b2b_bonus {
            transient_eval += self.back_to_back;
        }

        let highest_point = *board.column_heights().iter().max().unwrap() as i32;
        transient_eval += self.top_quarter * (highest_point - 15).max(0);
        transient_eval += self.top_half * (highest_point - 10).max(0);
        transient_eval += self.height * highest_point;

        acc_eval += self.jeopardy * (highest_point - 10).max(0) * if self.timed_jeopardy { move_time } else { 10 } / 10;

        // Find lowest well column
        let mut well = 0;
        for x in 1..10 {
            if board.column_heights()[x] <= board.column_heights()[well] {
                well = x;
            }
        }

        // Add bumpiness
        let (bump, bump_sq) = bumpiness(board, well);
        transient_eval += self.bumpiness * bump;        //
        transient_eval += self.bumpiness * bump_sq;     //

        // Add cavities and overhangs
        let (cavity_cells, overhang_cells) = cavities_and_overhangs(board);
        transient_eval += cavity_cells * self.cavity_cells;      // * self.cavity_cells
        transient_eval += cavity_cells * cavity_cells; // * self.cavity_cells_sq
        transient_eval += overhang_cells * self.cavity_cells_sq;    // * self.overhang_cells
        transient_eval += overhang_cells * overhang_cells * self.overhang_cells_sq; // * self.overhang_cells_sq

        // Add covered cell metrics
        let (covered, covered_sq) = covered_cells(board);
        transient_eval += covered * self.covered_cells;      // * self.covered_cells
        transient_eval += covered_sq * self.covered_cells_sq;   // * self.covered_cells_sq

        // Add T-slot cutout estimation
        let ts = if self.use_bag {
            board.next_bag().contains(Piece::T) as usize
                + (board.next_bag().len() <= 3) as usize
                + (board.hold_piece == Some(Piece::T)) as usize
        } else {
            1 + (board.hold_piece == Some(Piece::T)) as usize
        };

        let mut board = board.clone();
        for _ in 0..ts {
            let cutout_location = sky_tslot_left(&board)
                .or_else(|| sky_tslot_right(&board))
                .or_else(|| {
                    let tst = tst_twist_left(&board).or_else(|| tst_twist_right(&board))?;
                    cave_tslot(&board, tst).or_else(|| {
                        let corners = board.occupied(tst.x - 1, tst.y - 1) as usize
                            + board.occupied(tst.x + 1, tst.y - 1) as usize
                            + board.occupied(tst.x - 1, tst.y + 1) as usize
                            + board.occupied(tst.x + 1, tst.y + 1) as usize;
                        if corners >= 3 && board.on_stack(&tst) {
                            Some(tst)
                        } else {
                            None
                        }
                    })
                })
                .or_else(|| fin_left(&board))
                .or_else(|| fin_right(&board));
            let result = match cutout_location {
                Some(location) => cutout_tslot(board.clone(), location),
                None => break,
            };
            transient_eval += self.tslot[result.lines];
            if let Some(b) = result.result {
                board = b;
            } else {
                break;
            }
        }

        (transient_eval, acc_eval)
    }
}