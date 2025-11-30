import { fileSearchTool, hostedMcpTool, codeInterpreterTool, RunContext, Agent, AgentInputItem, Runner, withTrace } from "@openai/agents";
import { OpenAI } from "openai";
import { z } from "zod";


// Tool definitions
const fileSearch = fileSearchTool([
  "vs_6928ccc617c48191967447061a4396f0"
])
const mcp = hostedMcpTool({
  serverLabel: "GitHub_MCP",
  allowedTools: [
    "add_comment_to_pending_review",
    "add_issue_comment",
    "assign_copilot_to_issue",
    "create_branch",
    "create_or_update_file",
    "create_pull_request",
    "create_repository",
    "delete_file",
    "fork_repository",
    "get_commit",
    "get_file_contents",
    "get_label",
    "get_latest_release",
    "get_me",
    "get_release_by_tag",
    "get_tag",
    "get_team_members",
    "get_teams",
    "issue_read",
    "issue_write",
    "list_branches",
    "list_commits",
    "list_issue_types",
    "list_issues",
    "list_pull_requests",
    "list_releases",
    "list_tags",
    "merge_pull_request",
    "pull_request_read",
    "pull_request_review_write",
    "push_files",
    "request_copilot_review",
    "search_code",
    "search_issues",
    "search_pull_requests",
    "search_repositories",
    "search_users",
    "sub_issue_write",
    "update_pull_request",
    "update_pull_request_branch"
  ],
  authorization: "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",
  requireApproval: "always",
  serverUrl: "https://api.githubcopilot.com/mcp"
})
const codeInterpreter = codeInterpreterTool({
  container: {
    type: "auto",
    file_ids: [
      "file-W12zqXJpS5jQeYEve6QrLB",
      "file-BRbnrBxHnPNqpkuEcxq1V6",
      "file-KCovpfXNytysNKF55kRb7K",
      "file-2WD7XTqK2vycim1yqGSZ9A",
      "file-JyELhe5wscp479AZeqCtNc",
      "file-5u58vapVdQviveywNYc6qN",
      "file-P1ZcbjcNikLaog4q8VjoKA",
      "file-NHwHCP8HkjBEApJLcactw1"
    ]
  }
})
const codeInterpreter1 = codeInterpreterTool({
  container: {
    type: "auto",
    file_ids: []
  }
})

// Shared client for guardrails and file search
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const AgentUnderstandUiRequestSchema = z.object({ intent: z.string(), has_enough_details: z.boolean(), missing_details: z.array(z.string()), summary: z.string() });
interface AgentUnderstandUiRequestContext {
  stateInput: string;
}
const agentUnderstandUiRequestInstructions = (runContext: RunContext<AgentUnderstandUiRequestContext>, _agent: Agent<AgentUnderstandUiRequestContext>) => {
  const { stateInput } = runContext.context;
  return `Você é um engenheiro frontend sênior especializado em Next.js App Router, React, React Three Fiber/Drei, Three.js, Tailwind CSS, TypeScript, WebGL e Framer Motion.
${stateInput}
Sua tarefa é ENTENDER perfeitamente o pedido do usuário e produzir um RESUMO ESTRUTURADO do que ele quer, avaliando se já é possível gerar o componente ou se ainda faltam informações.

======================================================================
O QUE VOCÊ DEVE FAZER
======================================================================

1. Leia o pedido do usuário com atenção.
2. Classifique a intenção *exata* do pedido em UMA das opções abaixo:

   • generate_component  
   • fix_code  
   • explain_code  
   • create_3d_scene  
   • debug_error  
   • improve_code  

3. Avalie se existem informações suficientes para começar a implementação:
   • Se tudo estiver claro → has_enough_details = true  
   • Se faltar QUALQUER detalhe necessário → has_enough_details = false

4. Liste cada detalhe que falta em \"missing_details\".

5. Resuma tudo o que o usuário pediu em \"summary\", de forma direta e clara.

6. NÃO escreva comentários, explicações ou texto fora do JSON final.

======================================================================
FORMATO DE SAÍDA (OBRIGATÓRIO)
======================================================================

Você DEVE responder **exclusivamente** com este JSON:

{
  \"intent\": \"[uma das opções acima]\",
  \"has_enough_details\": true | false,
  \"missing_details\": [\"item 1\", \"item 2\", ...],
  \"summary\": \"[resumo objetivo do pedido]\"
}

======================================================================
REGRAS
======================================================================

• Seja rigoroso: se faltar algo essencial, marque has_enough_details = false.  
• Nunca invente detalhes.  
• Nunca explique fora do JSON.  
• Nunca inclua texto antes ou depois do JSON.   `
}
const agentUnderstandUiRequest = new Agent({
  name: "Agent – Understand UI Request",
  instructions: agentUnderstandUiRequestInstructions,
  model: "gpt-4.1",
  tools: [
    fileSearch,
    mcp
  ],
  outputType: AgentUnderstandUiRequestSchema,
  modelSettings: {
    temperature: 1,
    topP: 1,
    maxTokens: 2048,
    store: true
  }
});

const agentAskForMoreDetails = new Agent({
  name: "Agent – Ask for More Details",
  instructions: `Você recebe state.parsed_request.missing_details, que contém uma lista de informações que ainda faltam para executar o pedido do usuário.

Sua tarefa é pedir ao usuário APENAS essas informações que faltam.

======================================================================
REGRAS
======================================================================

1. Pergunte TODOS os itens de missing_details em UMA ÚNICA mensagem.
2. Não gere código.
3. Não sugira implementação.
4. Não acrescente nada além das perguntas necessárias.
5. Não reescreva o pedido original.
6. Não dê exemplos ou explicações.

======================================================================
FORMATO DA RESPOSTA
======================================================================

Mensagem simples, direta e objetiva, assim:

“Para continuar, preciso que você me informe:
1) [detalhe 1]
2) [detalhe 2]
3) [detalhe 3]
...”

======================================================================

Você deve montar essa lista usando EXCLUSIVAMENTE:

`,
  model: "gpt-5.1",
  tools: [
    fileSearch
  ],
  modelSettings: {
    reasoning: {
      effort: "low",
      summary: "auto"
    },
    store: true
  }
});

interface AgentGenerateComponentContext {
  stateUserInput: string;
  stateParsedRequest: string;
}
const agentGenerateComponentInstructions = (runContext: RunContext<AgentGenerateComponentContext>, _agent: Agent<AgentGenerateComponentContext>) => {
  const { stateUserInput, stateParsedRequest } = runContext.context;
  return `Você é um engenheiro frontend sênior especializado em:

• Next.js App Router (TypeScript)
• React
• React Three Fiber (R3F)
• Drei
• Three.js
• Tailwind CSS
• Framer Motion
• GLTF/GLB loading
• WebGL e materiais avançados (refraction, transmission, shaders)

Seu objetivo é GERAR O CÓDIGO FINAL E COMPLETO solicitado pelo usuário, sempre seguindo EXATAMENTE:

• O pedido original do usuário: ${stateUserInput}
• O parsed request: ${stateParsedRequest}
• Os padrões encontrados no File Search (quando existirem)
• As práticas modernas do ecossistema Next.js + React + R3F + TS + Tailwind + Framer Motion

======================================================================
REGRAS OBRIGATÓRIAS
======================================================================

1. Sempre gere um ARQUIVO COMPLETO (ou múltiplos arquivos, se necessário).
2. Inclua todos os elementos exigidos:
   - imports
   - JSX/TSX completo
   - Canvas R3F
   - Lights, materials, meshes, helpers
   - Animações (Framer Motion ou R3F)
   - Responsividade e estrutura Next.js App Router
3. NÃO invente APIs.  
   Use somente padrões encontrados no File Search OU práticas oficiais da stack.
4. Nunca escreva comentários do tipo “insert code here”.
5. Nunca omita partes essenciais do código.
6. A estrutura deve ser IMEDIATAMENTE COLÁVEL no projeto.
7. Se o pedido original estiver incompleto ou ambíguo, faça a melhor interpretação possível **sem inventar funcionalidades externas ao pedido**.
8. Se for solução de debugging:
   - explique claramente o erro encontrado
   - gere a versão corrigida DO ARQUIVO COMPLETO

======================================================================
FORMATO DE SAÍDA (OBRIGATÓRIO)
======================================================================

Responda EXCLUSIVAMENTE neste formato:

```tsx
// código completo final aqui
...

Logo abaixo:

Como usar este componente:

[instruções curtas e diretas de uso no Next.js App Router]


E finalize SEMPRE com a frase:

“Antes de finalizar, deseja revisar ou ajustar algo?”

======================================================================


NOTAS IMPORTANTES


• Respeite a estrutura atual do projeto.
Não altere pastas nem convencões, a menos que o pedido peça explicitamente.

• Priorize as práticas encontradas no File Search.
Se houver exemplos próximos no repositório, siga-os.

• O código deve ser funcional, otimizado e claro.

• Se o componente envolver 3D, shaders ou animações:

otimize performance (useFrame, memo, suspense, reuse materials, etc.)
use materiais de Drei quando possível
siga padrões oficiais da documentação R3F/Drei
`
}
const agentGenerateComponent = new Agent({
  name: "Agent – Generate Component",
  instructions: agentGenerateComponentInstructions,
  model: "gpt-5.1",
  tools: [
    fileSearch,
    codeInterpreter,
    mcp
  ],
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

const agentCorrection = new Agent({
  name: "Agent - correction",
  instructions: `O resultado gerado anteriormente está incorreto, incompleto ou insatisfatório.

Quero que você faça o seguinte processo:

1. **Reanalise cuidadosamente a minha solicitação original.**
2. **Compare** a solicitação com a resposta anterior que você gerou.
3. **Identifique claramente**:
   - partes incorretas
   - partes incompletas
   - partes que não atendem aos requisitos
4. **Explique o motivo do erro** de forma objetiva.
5. **Gere uma nova resposta corrigida**, agora:
   - funcional,
   - completa,
   - seguindo exatamente o que foi pedido,
   - e aplicando boas práticas do ecossistema solicitado (Next.js, React, React Three Fiber, Drei, TypeScript etc.).
6. **Valide mentalmente** se a nova resposta atende 100% ao pedido antes de enviar.
7. Só então **entregue a versão final**.

Se necessário, revise a documentação interna disponível no vector store para corrigir comportamentos, padrões ou implementação.`,
  model: "gpt-5.1",
  tools: [
    fileSearch
  ],
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

interface AgentReviewCodeContext {
  stateUserInput: string;
  stateGeneratedComponent: string;
}
const agentReviewCodeInstructions = (runContext: RunContext<AgentReviewCodeContext>, _agent: Agent<AgentReviewCodeContext>) => {
  const { stateUserInput, stateGeneratedComponent } = runContext.context;
  return `Você é um agente de correção de código especializado em:

• Next.js App Router (TypeScript)
• React
• React Three Fiber / Drei / Three.js
• Tailwind CSS
• Framer Motion
• Boas práticas de arquitetura, padrões e performance para projetos modernos

Você SEMPRE recebe:

1. O PEDIDO ORIGINAL DO USUÁRIO  →  ${stateUserInput}
2. O CÓDIGO ATUAL GERADO PARA REVISÃO  →  ${stateGeneratedComponent}

Sua missão é produzir uma versão revisada, corrigida, otimizada e totalmente funcional do código, garantindo aderência total ao pedido original e às práticas do ecossistema.

======================================================================
TAREFAS OBRIGATÓRIAS
======================================================================

1. Leia cuidadosamente o PEDIDO ORIGINAL.
2. Compare com o CÓDIGO ATUAL e identifique:
   - requisitos não atendidos
   - problemas estruturais
   - más práticas
   - erros de tipagem
   - incoerências com Next.js App Router
   - problemas em R3F/Drei/Three
   - problemas de Tailwind / layout / UI
   - ausência ou falhas de animações (Framer Motion)
3. Liste os problemas encontrados.
4. Gere uma NOVA VERSÃO DO CÓDIGO:
   - completa
   - funcional
   - pronta para uso imediato
   - preservando a assinatura e a API pública (a menos que o pedido peça o contrário)
5. Otimize arquitetura, estrutura, imports, tipagem e performance.
6. Valide mentalmente que o código final atende 100% ao pedido antes de entregar.
7. NÃO inclua textos fora do formato de saída obrigatório.

======================================================================
FORMATO DE SAÍDA (OBRIGATÓRIO — SEM NADA FORA DISSO)
======================================================================

```tsx
// código completo revisado aqui
// (arquivo ou arquivos prontos para colar no projeto)
...
Motivos da reprovação:

…


Melhorias aplicadas:

…


Dúvidas ou decisões em trechos incertos (se houver):

…
`
}
const agentReviewCode = new Agent({
  name: " Agent – Review Code",
  instructions: agentReviewCodeInstructions,
  model: "gpt-5.1",
  tools: [
    fileSearch,
    codeInterpreter1
  ],
  modelSettings: {
    reasoning: {
      effort: "high",
      summary: "auto"
    },
    store: true
  }
});

const approvalRequest = (message: string) => {

  // TODO: Implement
  return true;
}

type WorkflowInput = { input_as_text: string };


// Main code entrypoint
export const runWorkflow = async (workflow: WorkflowInput) => {
  return await withTrace("AGENT DEV NEXT JS", async () => {
    const state = {
      imput: "Set state – Save Parsed Request",
      input: "parsed_request",
      parsed_request: null,
      project_data: null,
      generated_component: null,
      parsed_requesta: "parsed_request = <agent_output>",
      agentoutput: " agent.output",
      stateproject_code_context: null,
      user_input: null,
      statereviewed_component: null
    };
    const conversationHistory: AgentInputItem[] = [
      { role: "user", content: [{ type: "input_text", text: workflow.input_as_text }] }
    ];
    const runner = new Runner({
      traceMetadata: {
        __trace_source__: "agent-builder",
        workflow_id: "wf_692b7c6d61648190aa432ff388b66fdf02934a1cf8be4877"
      }
    });
    const agentUnderstandUiRequestResultTemp = await runner.run(
      agentUnderstandUiRequest,
      [
        ...conversationHistory
      ],
      {
        context: {
          stateInput: state.input
        }
      }
    );
    conversationHistory.push(...agentUnderstandUiRequestResultTemp.newItems.map((item) => item.rawItem));

    if (!agentUnderstandUiRequestResultTemp.finalOutput) {
        throw new Error("Agent result is undefined");
    }

    const agentUnderstandUiRequestResult = {
      output_text: JSON.stringify(agentUnderstandUiRequestResultTemp.finalOutput),
      output_parsed: agentUnderstandUiRequestResultTemp.finalOutput
    };
    state.user_input = agentUnderstandUiRequestResult.output_text == agentUnderstandUiRequestResult.output_parsed.has_enough_details;
    if (agentUnderstandUiRequestResult.output_parsed.has_enough_details == true) {
      const agentAskForMoreDetailsResultTemp = await runner.run(
        agentAskForMoreDetails,
        [
          ...conversationHistory
        ]
      );
      conversationHistory.push(...agentAskForMoreDetailsResultTemp.newItems.map((item) => item.rawItem));

      if (!agentAskForMoreDetailsResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentAskForMoreDetailsResult = {
        output_text: agentAskForMoreDetailsResultTemp.finalOutput ?? ""
      };
      state.agentoutput = agentAskForMoreDetailsResult.output_text;
      const filesearchResult = (await client.vectorStores.search("vs_6928ccc617c48191967447061a4396f0", {query: ``
    Search for relevant source code, patterns, components, structures or examples
    from the repositories included in the vector store.
    Prioritize:

    Next.js App Router structures
    React Three Fiber scenes
    Drei helpers
    Three.js materials, lighting, controls
    GLTF/GLB loading patterns
    Shaders (GLSL)
    Scroll-based animations
    Glass distortion effects
    Scene composition and performance patterns

    Return ONLY the code snippets and meaningful context needed for the next step.

     {{state.stateproject_code_context}}``,
      max_num_results: 20})).data.map((result) => {
        return {
          id: result.file_id,
          filename: result.filename,
          score: result.score,
        }
      });
      state.input = state.parsed_request;
      state.stateproject_code_context = state.stateproject_code_context;
      const agentGenerateComponentResultTemp = await runner.run(
        agentGenerateComponent,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateParsedRequest: state.parsed_request
          }
        }
      );
      conversationHistory.push(...agentGenerateComponentResultTemp.newItems.map((item) => item.rawItem));

      if (!agentGenerateComponentResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentGenerateComponentResult = {
        output_text: agentGenerateComponentResultTemp.finalOutput ?? ""
      };
      state.generated_component = agentGenerateComponentResult.output_text;
      state.input = state.user_input == workflow.input_as_text;
      const agentReviewCodeResultTemp = await runner.run(
        agentReviewCode,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateGeneratedComponent: state.generated_component
          }
        }
      );
      conversationHistory.push(...agentReviewCodeResultTemp.newItems.map((item) => item.rawItem));

      if (!agentReviewCodeResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentReviewCodeResult = {
        output_text: agentReviewCodeResultTemp.finalOutput ?? ""
      };
      state.statereviewed_component = agentReviewCodeResult.output_text;
      const approvalMessage = `This node pauses the workflow for human review.

    You are seeing the component generated by the agent.

    Please review:
    - Overall API and props
    - Code style and readability
    - Correct use of Next.js App Router, Tailwind, React Three Fiber, and Framer Motion
    - Any potential performance or security issues

    Approve to send it to the user, or reject and adjust the prompt/manual code as needed.`;

      if (approvalRequest(approvalMessage)) {
          state.agentoutput = state.statereviewed_component;
          return agentReviewCodeResult;
      } else {
          state.agentoutput = state.statereviewed_component;
          const agentCorrectionResultTemp = await runner.run(
            agentCorrection,
            [
              ...conversationHistory
            ]
          );
          conversationHistory.push(...agentCorrectionResultTemp.newItems.map((item) => item.rawItem));

          if (!agentCorrectionResultTemp.finalOutput) {
              throw new Error("Agent result is undefined");
          }

          const agentCorrectionResult = {
            output_text: agentCorrectionResultTemp.finalOutput ?? ""
          };
          return agentCorrectionResult;
      }
    } else if (agentUnderstandUiRequestResult.output_parsed.has_enough_details == false) {
      const filesearchResult = (await client.vectorStores.search("vs_6928ccc617c48191967447061a4396f0", {query: ``
    Search for relevant source code, patterns, components, structures or examples
    from the repositories included in the vector store.
    Prioritize:

    Next.js App Router structures
    React Three Fiber scenes
    Drei helpers
    Three.js materials, lighting, controls
    GLTF/GLB loading patterns
    Shaders (GLSL)
    Scroll-based animations
    Glass distortion effects
    Scene composition and performance patterns

    Return ONLY the code snippets and meaningful context needed for the next step.

     {{state.stateproject_code_context}}``,
      max_num_results: 20})).data.map((result) => {
        return {
          id: result.file_id,
          filename: result.filename,
          score: result.score,
        }
      });
      state.input = state.parsed_request;
      state.stateproject_code_context = state.stateproject_code_context;
      const agentGenerateComponentResultTemp = await runner.run(
        agentGenerateComponent,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateParsedRequest: state.parsed_request
          }
        }
      );
      conversationHistory.push(...agentGenerateComponentResultTemp.newItems.map((item) => item.rawItem));

      if (!agentGenerateComponentResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentGenerateComponentResult = {
        output_text: agentGenerateComponentResultTemp.finalOutput ?? ""
      };
      state.generated_component = agentGenerateComponentResult.output_text;
      state.input = state.user_input == workflow.input_as_text;
      const agentReviewCodeResultTemp = await runner.run(
        agentReviewCode,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateGeneratedComponent: state.generated_component
          }
        }
      );
      conversationHistory.push(...agentReviewCodeResultTemp.newItems.map((item) => item.rawItem));

      if (!agentReviewCodeResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentReviewCodeResult = {
        output_text: agentReviewCodeResultTemp.finalOutput ?? ""
      };
      state.statereviewed_component = agentReviewCodeResult.output_text;
      const approvalMessage = `This node pauses the workflow for human review.

    You are seeing the component generated by the agent.

    Please review:
    - Overall API and props
    - Code style and readability
    - Correct use of Next.js App Router, Tailwind, React Three Fiber, and Framer Motion
    - Any potential performance or security issues

    Approve to send it to the user, or reject and adjust the prompt/manual code as needed.`;

      if (approvalRequest(approvalMessage)) {
          state.agentoutput = state.statereviewed_component;
          return agentReviewCodeResult;
      } else {
          state.agentoutput = state.statereviewed_component;
          const agentCorrectionResultTemp = await runner.run(
            agentCorrection,
            [
              ...conversationHistory
            ]
          );
          conversationHistory.push(...agentCorrectionResultTemp.newItems.map((item) => item.rawItem));

          if (!agentCorrectionResultTemp.finalOutput) {
              throw new Error("Agent result is undefined");
          }

          const agentCorrectionResult = {
            output_text: agentCorrectionResultTemp.finalOutput ?? ""
          };
          return agentCorrectionResult;
      }
    } else {
      const filesearchResult = (await client.vectorStores.search("vs_6928ccc617c48191967447061a4396f0", {query: ``
    Search for relevant source code, patterns, components, structures or examples
    from the repositories included in the vector store.
    Prioritize:

    Next.js App Router structures
    React Three Fiber scenes
    Drei helpers
    Three.js materials, lighting, controls
    GLTF/GLB loading patterns
    Shaders (GLSL)
    Scroll-based animations
    Glass distortion effects
    Scene composition and performance patterns

    Return ONLY the code snippets and meaningful context needed for the next step.

     {{state.stateproject_code_context}}``,
      max_num_results: 20})).data.map((result) => {
        return {
          id: result.file_id,
          filename: result.filename,
          score: result.score,
        }
      });
      state.input = state.parsed_request;
      state.stateproject_code_context = state.stateproject_code_context;
      const agentGenerateComponentResultTemp = await runner.run(
        agentGenerateComponent,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateParsedRequest: state.parsed_request
          }
        }
      );
      conversationHistory.push(...agentGenerateComponentResultTemp.newItems.map((item) => item.rawItem));

      if (!agentGenerateComponentResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentGenerateComponentResult = {
        output_text: agentGenerateComponentResultTemp.finalOutput ?? ""
      };
      state.generated_component = agentGenerateComponentResult.output_text;
      state.input = state.user_input == workflow.input_as_text;
      const agentReviewCodeResultTemp = await runner.run(
        agentReviewCode,
        [
          ...conversationHistory
        ],
        {
          context: {
            stateUserInput: state.user_input,
            stateGeneratedComponent: state.generated_component
          }
        }
      );
      conversationHistory.push(...agentReviewCodeResultTemp.newItems.map((item) => item.rawItem));

      if (!agentReviewCodeResultTemp.finalOutput) {
          throw new Error("Agent result is undefined");
      }

      const agentReviewCodeResult = {
        output_text: agentReviewCodeResultTemp.finalOutput ?? ""
      };
      state.statereviewed_component = agentReviewCodeResult.output_text;
      const approvalMessage = `This node pauses the workflow for human review.

    You are seeing the component generated by the agent.

    Please review:
    - Overall API and props
    - Code style and readability
    - Correct use of Next.js App Router, Tailwind, React Three Fiber, and Framer Motion
    - Any potential performance or security issues

    Approve to send it to the user, or reject and adjust the prompt/manual code as needed.`;

      if (approvalRequest(approvalMessage)) {
          state.agentoutput = state.statereviewed_component;
          return agentReviewCodeResult;
      } else {
          state.agentoutput = state.statereviewed_component;
          const agentCorrectionResultTemp = await runner.run(
            agentCorrection,
            [
              ...conversationHistory
            ]
          );
          conversationHistory.push(...agentCorrectionResultTemp.newItems.map((item) => item.rawItem));

          if (!agentCorrectionResultTemp.finalOutput) {
              throw new Error("Agent result is undefined");
          }

          const agentCorrectionResult = {
            output_text: agentCorrectionResultTemp.finalOutput ?? ""
          };
          return agentCorrectionResult;
      }
    }
  });
}
