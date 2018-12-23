mod random_drafter;
mod api;
use crate::api::*;
extern crate clap;
use clap::{Arg, App};
use std::fs::File;
use std::io::{prelude::*, BufReader};
use rand::seq::SliceRandom;
use rand::Rng;

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

    println!("draft packs: {:?}", draft_packs);

    // TODO: Implement full draft of random drafters
    let drafter = random_drafter::RandomDrafter {};

    let pack = &draft_packs[0][0];
    let cards_owned : Vec<api::Card> = vec![];

    println!("Random drafter's pick: {}", drafter.pick(&pack, &cards_owned, &draft_info));
}

fn create_draft_info(cube_list_filename: &String) -> DraftInfo {
    // from https://stackoverflow.com/a/35820003
    let list_file = File::open(cube_list_filename).expect("file not found");
    let buf = BufReader::new(list_file);
    let cube_list: Vec<Card> = buf.lines()
        .map(|l| Card::new(&l.expect("Could not parse line")))
        .collect();

    DraftInfo {
        card_list: cube_list,
        num_drafters: 6,
        num_packs: 3,
        cards_per_pack: 15
    }
}

// Returns shuffled draft packs in the following format:
// Outermost vector: which pack (e.g. drafts normally have 3 packs per player)
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

    for pack_index in 0..draft_info.num_packs {
        let mut pack_set = vec![];

        for seat_index in 0..draft_info.num_drafters {
            let start_index = ((pack_index * draft_info.num_drafters + seat_index)* draft_info.cards_per_pack) as usize;
            let end_index = start_index + (draft_info.cards_per_pack as usize);
            println!("start index: {}", start_index);
            let slice: &[Card] = &shuffled_list[start_index..end_index];
            pack_set.push(slice.to_vec());
        }

        draft_packs.push(pack_set);
    }

    draft_packs
}