package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"
)

type Params struct {
	S0               float64 `json:"s0"`
	SigmaCrude       float64 `json:"sigma_crude"`
	JumpLambda       float64 `json:"jump_lambda"`
	JumpMu           float64 `json:"jump_mu"`
	CrackGas0        float64 `json:"crack_gas_0"`
	CrackDiesel0     float64 `json:"crack_diesel_0"`
	SigmaCrackGas    float64 `json:"sigma_crack_gas"`
	SigmaCrackDiesel float64 `json:"sigma_crack_diesel"`
}

const (
	Days  = 180
	Sims  = 10000
	Dt    = 1.0 / 365.0
	Mu    = 0.05
	TaxG  = 0.57
	DistG = 0.65
	TaxD  = 0.65
	DistD = 0.85
)

func main() {
	rand.Seed(time.Now().UnixNano())

	file, err := os.Open("params.json")
	if err != nil {
		panic("Run calibrate.py first to generate params.json")
	}
	defer file.Close()

	var p Params
	json.NewDecoder(file).Decode(&p)

	var wg sync.WaitGroup
	gasResults := make([][]string, Sims)
	dieselResults := make([][]string, Sims)

	fmt.Println("Running 10,000 parallel paths...")
	for i := 0; i < Sims; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			st := p.S0
			cGas := p.CrackGas0
			cDies := p.CrackDiesel0

			gasPath := make([]string, Days)
			diesPath := make([]string, Days)

			for t := 0; t < Days; t++ {
				z := rand.NormFloat64()

				jump := 0.0
				if rand.Float64() < (p.JumpLambda * Dt) {
					jump = math.Exp(rand.NormFloat64()*0.05 + p.JumpMu)
				}

				dS := Mu*st*Dt + p.SigmaCrude*st*math.Sqrt(Dt)*z + jump*st
				st += dS

				cGas += rand.NormFloat64() * p.SigmaCrackGas * 0.1
				cDies += rand.NormFloat64() * p.SigmaCrackDiesel * 0.1

				gasPrice := (st / 42.0) + (cGas / 42.0) + TaxG + DistG
				diesPrice := (st / 42.0) + (cDies / 42.0) + TaxD + DistD

				gasPath[t] = strconv.FormatFloat(gasPrice, 'f', 2, 64)
				diesPath[t] = strconv.FormatFloat(diesPrice, 'f', 2, 64)
			}
			gasResults[idx] = gasPath
			dieselResults[idx] = diesPath
		}(i)
	}
	wg.Wait()

	writeCSV("results_gas.csv", gasResults)
	writeCSV("results_diesel.csv", dieselResults)
	fmt.Println("Simulation complete. Output saved to CSVs.")
}

func writeCSV(filename string, data [][]string) {
	file, _ := os.Create(filename)
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	writer.WriteAll(data)
}
