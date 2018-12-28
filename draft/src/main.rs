#![feature(vec_remove_item)]

mod random_drafter;
mod api;
use crate::api::*;
extern crate clap;
use clap::{Arg, App};
use std::fs::File;
use std::io::{prelude::*, BufReader};
use rand::seq::SliceRandom;

fn main() {
    let matches = App::new("Drafting")
        .arg(Arg::with_name("list")
                    .short("l")
                    .long("list")
                    .help("Text file containing full cube list (one card name per line)")
                    .takes_value(true)
                    .required(true))
        .get_matches();

    let list_filename = matches.value_of("list").unwrap().to_string();

    println!("list filename: {}", list_filename);

    let draft_info = create_draft_info(&list_filename);
    let mut draft_packs = create_draft_packs(&draft_info);

    let mut drafters: Vec<Box<Drafter>> = vec![];
    for _i in 0..draft_info.num_drafters {
        drafters.push(Box::new(random_drafter::RandomDrafter {}));
    }

    let mut draft_state = DraftState::new(drafters, draft_packs);
    println!("draft state: {:?}", draft_state);

    run_draft(&draft_info, &mut draft_state);
}

// Runs through a draft with the configuration specified by draft_info and pack list in draft_state,
// delegates picks to the drafter implementations in draft_state, and writes the picked cards to draft_state.
fn run_draft(draft_info: &DraftInfo, draft_state: &mut DraftState) {

    // "Draft phase" is commonly referred to as "Pack" by magic players, e.g. "Pack 1 pick 5".
    // A typical draft has 3 draft phases.
    for draft_phase in 0..draft_info.num_phases {
        println!("======= draft phase: {} =======", draft_phase);

        // Alternate passing directions based on phase, starting with passing left.
        let direction: i32 = if draft_phase % 2 == 0 {1} else {-1};

        // "Pick index" is the "pick 1" part of "Pack 1 pick 5". In each phase, we repeat
        // picking a card and passing until we've picked all the cards in the pack.
        for pick_index in 0..draft_info.cards_per_pack {
            println!("== pick {} ==", pick_index);

            // Have each drafter make a pick.
            for drafter_index in 0..draft_info.num_drafters {
                // We implement "passing" the packs after each pick by shifting the index of the pack
                // that a drafter will pick from by the pick_index. We add it when passing left, and subtract
                // when passing right (you can picture this like the packs staying in place and the drafters
                // standing up and walking around the table).
                // Then we apply modulus (since the packs are passed in a circle).
                let mut current_pack_index: i32 = drafter_index as i32 + direction * pick_index as i32;
                current_pack_index = current_pack_index % draft_info.num_drafters as i32;
                // The mod of a negative number will remain negative, e.g. -11 mod 8 = -3, but we want to
                // translate that into the positive equivalent to find the index into the packs, so
                // we add num_drafters after the mod if it's a negative number. So in our example, -3
                // would become 5. This represents starting at seat 0 and finding the drafter 3 seats to the left,
                // which would be the drafter at seat 5.
                if current_pack_index < 0 {
                    current_pack_index += draft_info.num_drafters as i32;
                }
                let current_pack_index = current_pack_index as usize;
                println!("Drafter {} picking from {}", drafter_index, current_pack_index);

                let owned_cards= &mut (draft_state.owned_cards)[drafter_index];
                let drafter: &Box<Drafter> = &draft_state.drafters[drafter_index];

                // TODO: I think this clone shouldn't be necessary, but I couldn't figure out how to remove it,
                // since otherwise both a mutable and immutable borrow will occur
                let current_pack = &draft_state.packs[draft_phase][current_pack_index].clone();
                let picked_card = drafter.pick(current_pack, owned_cards, &draft_info);
                println!("Current pack: {:?}", current_pack);
                println!("Picked card: {:?}\n", picked_card);
                let picked_card = draft_state.packs[draft_phase][current_pack_index].remove_item(picked_card)
                    .expect("could not remove card");
                owned_cards.push(picked_card);
            }
        }
    }

    println!("draft state: {:?}", draft_state);
}

fn create_draft_info(cube_list_filename: &str) -> DraftInfo {
    // from https://stackoverflow.com/a/35820003
    let list_file = File::open(cube_list_filename).expect("file not found");
    let buf = BufReader::new(list_file);
    let cube_list: Vec<Card> = buf.lines()
        .map(|l| Card::new(&l.expect("Could not parse line")))
        .collect();

    DraftInfo {
        card_list: cube_list,
        num_drafters: 6,
        num_phases: 3,
        cards_per_pack: 15
    }
}

// Returns shuffled draft packs in the following format:
// Outermost vector: draft phases (e.g. in a normal draft there's 3 phases, which are colloquially known as "Pack 1, Pack 2, Pack 3")
// second level of vector: which seat the pack will start at in the draft
// innermost: a pack of cards
fn create_draft_packs(draft_info: &DraftInfo) -> Vec<Vec<Vec<Card>>> {
    let mut rng = rand::thread_rng();
    let mut shuffled_list = draft_info.card_list.to_vec();
    shuffled_list.shuffle(&mut rng);

    // Outermost vector: which pack (e.g. drafts normally have 3 packs per player)
    // second level of vector: which seat the pack will start at in the draft
    // innermost: a pack of cards
    let mut draft_packs: Vec<Vec<Vec<Card>>> = vec![];

    for pack_index in 0..draft_info.num_phases {
        let mut pack_set = vec![];

        for seat_index in 0..draft_info.num_drafters {
            let start_index = ((pack_index * draft_info.num_drafters + seat_index) * draft_info.cards_per_pack) as usize;
            let end_index = start_index + (draft_info.cards_per_pack as usize);
            let slice: &[Card] = &shuffled_list[start_index..end_index];
            pack_set.push(slice.to_vec());
        }

        draft_packs.push(pack_set);
    }

    draft_packs
}