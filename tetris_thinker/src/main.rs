use libtetris::{
    chooser::ScoredBoard, evaluate::Standard, find_moves, Board, MovementMode, Piece, Row, SpawnRule
};
use enumset::EnumSet;
use serde::Deserialize;

#[derive(Deserialize)]
struct Input {
    piece: String,
    field: Vec<Vec<u8>>,     // 40 rows × 10 columns, bottom to top
    bag: Vec<String>,        // Remaining 7-bag pieces
    hold: Option<String>,    // Hold piece, or null
    next: Vec<String>,
    b2b: bool,
    combo: u32,
}

#[derive(serde::Serialize, Clone)]
struct Output {
    x: i32,
    y: i32,
    rotation: u8,
    inputs: Vec<String>,
    tspin: String,
    lines_cleared: usize,
    cleared_rows: Vec<i32>,
    used_hold: bool,
}

fn parse_piece(s: &str) -> Piece {
    match s {
        "I" => Piece::I,
        "O" => Piece::O,
        "T" => Piece::T,
        "S" => Piece::S,
        "Z" => Piece::Z,
        "J" => Piece::J,
        "L" => Piece::L,
        _ => panic!("Unknown piece type: {}", s),
    }
}

fn print_board<R: Row>(board: &Board<R>) {
    for y in (0..20).rev() {
        for x in 0..10 {
            let occupied = board.occupied(x, y);
            print!("{}", if occupied { "■" } else { "·" });
        }
        println!();
    }
    println!();
}

fn main() {
    let input_data = std::fs::read_to_string("input.json").expect("failed to read input.json");
    let input: Input = serde_json::from_str(&input_data).expect("invalid JSON");

    let mut field = [[false; 10]; 40];
    for (y, row) in input.field.iter().enumerate().take(40) {
        for (x, val) in row.iter().enumerate().take(10) {
            field[y][x] = *val != 0;
        }
    }

    let bag: EnumSet<Piece> = input.bag.iter().map(|s| parse_piece(s)).collect();
    let hold_piece = input.hold.as_ref().map(|s| parse_piece(s));

    let mut board = Board::new_with_state(field, bag, hold_piece, input.b2b, input.combo);
    for s in &input.next {
        let p = parse_piece(s);
        board.add_next_piece(p);
    }

    let current_piece = parse_piece(&input.piece);
    let mut spawn_candidates = vec![(current_piece, board.clone(), false)];

    match board.hold_piece {
        Some(hold_piece_type) if hold_piece_type != current_piece => {
            let mut swapped_board = board.clone();
            swapped_board.hold_piece = Some(current_piece);
            if let Some(_) = SpawnRule::Row19Or20.spawn(hold_piece_type, &swapped_board) {
                spawn_candidates.push((hold_piece_type, swapped_board, true));
            }
        },
        None => {
            if let Some(first_next_str) = input.next.first() {
                let new_current = parse_piece(first_next_str);
                let mut swapped_board = board.clone();
                swapped_board.hold_piece = Some(current_piece);
                if SpawnRule::Row19Or20.spawn(new_current, &swapped_board).is_some() {
                    spawn_candidates.push((new_current, swapped_board, true));
                }
            }
        },        
        _ => {},
    }
    // Reads in weights from `weights.json`. If certain weights are missing, defaults to what's in `evaluate.rs`.
    let config: Standard = {
        let weight_data = std::fs::read_to_string("weights.json").expect("failed to read weights.json");
        serde_json::from_str(&weight_data).expect("invalid weights.json")
    };
    let mut scored_candidates = Vec::new();
    let mut all_outputs = Vec::new();

    for (spawn_piece_type, board_variant, used_hold) in spawn_candidates {
        let spawn_piece = SpawnRule::Row19Or20
            .spawn(spawn_piece_type, &board_variant)
            .expect("Failed to spawn piece");

        let placements = find_moves(&board_variant, spawn_piece, MovementMode::ZeroG);

        for p in &placements {
            let mut new_board = board_variant.clone();
            let lock_result = new_board.lock_piece(p.location);

            print_board(&new_board);
            println!(
                "x: {}, y: {}, rotation: {}, tspin: {}, lines cleared: {}, cleared rows: {:?}\n",
                p.location.x,
                p.location.y,
                p.location.kind.1 as u8,
                format!("{:?}", p.location.tspin),
                lock_result.cleared_lines.len(),
                lock_result.cleared_lines
            );

            let output = Output {
                x: p.location.x,
                y: p.location.y,
                rotation: p.location.kind.1 as u8,
                inputs: p.inputs.movements.iter().map(|m| format!("{:?}", m)).collect(),
                tspin: format!("{:?}", p.location.tspin),
                lines_cleared: lock_result.cleared_lines.len(),
                cleared_rows: lock_result.cleared_lines.to_vec(),
                used_hold,
            };

            scored_candidates.push(((new_board, lock_result.clone(), 0, spawn_piece_type), output.clone()));
            all_outputs.push(output);
        }
    }

    println!("{}", serde_json::to_string_pretty(&all_outputs).unwrap());

    let (best_board, mut best_output) = scored_candidates
        .into_iter()
        .map(|((board, lock, mt, piece), output)| {
            let (transient, reward) = config.evaluate_board(&board, &lock, mt, piece);
            let score = transient + reward;
            (ScoredBoard { board, lock, score }, output)
        })
        .max_by_key(|(sb, _)| sb.score)
        .expect("No valid boards generated");

    if best_output.used_hold {
        best_output.inputs.insert(0, "Hold".to_string());
    }

    println!("\nBEST MOVE:");
    print_board(&best_board.board);
    println!(
        "score: {}, lines cleared: {}, placement kind: {:?} (b2b: {}, combo: {:?}, used hold: {})",
        best_board.score,
        best_board.lock.cleared_lines.len(),
        best_board.lock.placement_kind,
        best_board.lock.b2b,
        best_board.lock.combo,
        best_output.used_hold
    );
    println!("inputs for best move: {:?}", best_output.inputs);

    std::fs::write(
        "selected_actions.json",
        serde_json::to_string_pretty(&best_output.inputs).unwrap(),
    )
    .expect("Failed to write selected_actions.json");
}
